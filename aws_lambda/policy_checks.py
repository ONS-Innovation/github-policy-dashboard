import datetime
from dateutil.relativedelta import relativedelta
from requests import Response

from api_interface import api_controller


# Dependabot Alert Thresholds (Days)
critical_threshold = 5
high_threshold = 15
medium_threshold = 60
low_threshold = 90

# Inactive Threshold (Years)
inactive_threshold = 1

# Number of Commits to Check for Signed Commits
signed_commits_to_check = 15


# SLO Scripts

def get_response_for_alert_type(gh: api_controller, org: str, alert_type: str, page_no: int = 1, severity: str = "None") -> Response:
    if alert_type == "secret_scanning":
        return gh.get(f"https://api.github.com/orgs/{org}/secret-scanning/alerts", {"state": "open", "per_page":100, "page": page_no}, False)
    elif alert_type == "dependabot":
        return gh.get(f"https://api.github.com/orgs/{org}/dependabot/alerts", {"state": "open", "severity": severity, "per_page": 100, "page": page_no}, False)
    else:
        return "Error: Invalid Alert Type"

def get_security_alerts(gh: api_controller, org: str, days_open: int, alert_type: str, severity: str = "None") -> list[dict] | str:
    """Gets all open security alerts of a given type (either secret scanning or dependabot) that have been open for more than a given number of days, and are of a certain severity (dependabot only).

    Args:
        gh (api_controller): An instance of the api_controller class to make calls to the GitHub API
        org (str): The name of the organisation
        days_open (int): The number of days the alert has been open for
        alert_type (str): The type of alert to get (either secret_scanning or dependabot)
        severity (str, optional): The Severity of the alert. Defaults to "None". (dependabot only)

    Returns:
        list[dict] | str: A list of alerts or an error message
    """
    formatted_alerts = []

    alerts_response = get_response_for_alert_type(gh, org, alert_type, severity=severity)
    
    if alerts_response.status_code == 200:
        # Get Number of Pages 
        try:
            last_page = int(alerts_response.links["last"]["url"].split("=")[-1])
        except KeyError:
            # If Key Error, Last doesn't exist therefore 1 page
            last_page = 1

        for i in range(0, last_page):

            alerts_response = get_response_for_alert_type(gh, org, alert_type, page_no=i+1, severity=severity)

            if alerts_response.status_code == 200:
                alerts = alerts_response.json()

                comparison_date = datetime.datetime.today() - datetime.timedelta(days=days_open)

                for alert in alerts:
                    date_openned = datetime.datetime.strptime(alert["created_at"], "%Y-%m-%dT%H:%M:%SZ")

                    if date_openned < comparison_date:
                        days_openned = datetime.datetime.today() - date_openned

                        if alert_type == "dependabot":    
                            formatted_alert = {
                                "repo": alert["repository"]["name"],
                                "type": gh.get(alert["repository"]["url"], {}, False).json()["visibility"],
                                "dependency": alert["dependency"]["package"]["name"],
                                "advisory": alert["security_advisory"]["summary"],
                                "severity": alert["security_advisory"]["severity"],
                                "days_open": days_openned.days,
                                "link": alert["html_url"]
                            }
                        elif alert_type == "secret_scanning":
                            formatted_alert = {
                                "repo": alert["repository"]["name"],
                                "type": gh.get(alert["repository"]["url"], {}, False).json()["visibility"],
                                "secret": f"{alert["secret_type_display_name"]} - {alert["secret"]}",
                                "link": alert["html_url"]
                            }
                        else:
                            return "Error: Invalid Alert Type"

                        formatted_alerts.append(formatted_alert)

        return formatted_alerts
    else:
        return f"Error {alerts_response.status_code}: {alerts_response.json()["message"]}"
    

def get_all_dependabot_alerts(gh: api_controller, org: str) -> list[dict] | str:
    """
    Gets all open dependabot alerts using the following criteria:
        - Critical alerts open > critical_threshold days
        - High alerts open > high_threshold days
        - Medium alerts open > medium_threshold days
        - Low alerts open > low_threshold days

    Args:
        gh (api_controller): An instance of the api_controller class to make calls to the GitHub API
        org (str): The name of the organisation
    Returns:
        list[dict] (A list of formatted alerts)
        or
        str (an error has occured when accessing the API)
    """
    # Critical alerts open > critical_threshold days
    critical_alerts = get_security_alerts(gh, org, critical_threshold, "dependabot", "critical")

    # High alerts open > high_threshold days
    high_alerts = get_security_alerts(gh, org, high_threshold, "dependabot", "high")

    # Medium alerts open > medium_threshold days
    medium_alerts = get_security_alerts(gh, org, medium_threshold, "dependabot", "medium")

    # Low alerts open > low_threshold days
    low_alerts = get_security_alerts(gh, org, low_threshold, "dependabot", "low")

    if type(critical_alerts) == str or type(high_alerts) == str or type(medium_alerts) == str or type(low_alerts) == str:
        return "Error: An error has occured when accessing the API"
    else:
        alerts = critical_alerts + high_alerts + medium_alerts + low_alerts
        return alerts

# Repository Checks

# Repos not updated for > x yrs
def check_inactive(repo: dict) -> bool:
    """
    Checks if the repository was pushed to more than a year ago.
    If this is True, return True

    Args:
        repo (dict): The JSON response for the repository
    Returns:
        bool (True if check breaks policy)
    """

    last_update = datetime.datetime.strptime(repo["pushed_at"], "%Y-%m-%dT%H:%M:%SZ")

    comparison_date = datetime.datetime.today() - relativedelta(years=inactive_threshold)

    if last_update < comparison_date:
        return True
    else:
        return False

# Repos with no branch protection rules
def check_branch_protection(repo_api_url: str, gh: api_controller) -> bool | str:
    """
    Checks if all the branches in a repository are protected.
    If any branches are unprotected, return True

    Args:
        repo_api_url (str): The API endpoint to get the repository's branches
        gh (api_controller): An instance of the api_controller class to make calls to the GitHub API
    Returns:
        bool (True if check breaks policy)
        or
        str (an error has occured when accessing the API)
    """

    branches_response = gh.get(repo_api_url, {}, False)

    if branches_response.status_code == 200:
        json = branches_response.json()

        branches_unprotected = False
        unprotected_branches = []

        for branch in json:
            if branch["protected"] == False:
                branches_unprotected = True

                unprotected_branches.append(branch["name"])

        return branches_unprotected

    else:
        return f"Error {branches_response.status_code}: {branches_response.json()["message"]}"

# Repos with unsigned commits
def check_signed_commits(repo_api_url: str, gh: api_controller) -> bool | str:
    """
    Checks if the last signed_commits_to_check commits are signed.
    If any commit is not signed, return True

    Args:
        repo_api_url (str): The API endpoint to get the repository's commits
        gh (api_controller): An instance of the api_controller class to make calls to the GitHub API
    Returns:
        bool (True if check breaks policy)
        or
        str (an error has occured when accessing the API)
    """

    commits_response = gh.get(repo_api_url, {"per_page": signed_commits_to_check}, False)

    if commits_response.status_code == 200:
        commits = commits_response.json()

        unsigned_commits = False

        for commit in commits:
            if commit["commit"]["verification"]["verified"] == False:
                unsigned_commits = True

        return unsigned_commits
    elif commits_response.status_code == 409:
        # If error 409, then the repository does not have any commits.
        return False
    else:
        return f"Error {commits_response.status_code}: {commits_response.json()["message"]}"

# Repos without README.md, Liscense file (public only), 
# PIRR.md (private or internal) and .gitignore

def check_file_exists(repo_api_url: str, gh: api_controller, files: list[str]):
    """
    Checks if a given filename exists in the repository.
    Returns True if file is missing

    Args:
        repo_api_url (str): The API endpoint to get the repository's contents
        gh (api_controller): An instance of the api_controller class to make calls to the GitHub API
        files (list[str]): The list of filenames to look for
    Returns:
        bool (True if check breaks policy)
    """

    for file in files:
        if gh.get(repo_api_url.replace("{+path}", file), {}, False).status_code == 200:
            return False
        
    return True


# Any external PR's
def check_external_pr(repo_api_url: str, repo_full_name: str, gh: api_controller) -> bool | str:
    """
    Checks if there are any pull requests in the repository from non-members of the organisation.
    Returns True if there is an external pull request

    Args:
        repo_api_url (str): The API endpoint to get the repository's pull requests
        repo_full_name (str): The fullname of the repository from the GitHub API (format: <owner>/<repo>)
        gh (api_controller): An instance of the api_controller class to make calls to the GitHub API
    Returns:
        bool (True if check breaks policy)
        or
        str (an error has occured when accessing the API)
    """

    pulls_response = gh.get(repo_api_url, {}, False)

    org = repo_full_name.split("/")[0]

    org_members = []

    members_response = gh.get(f"/orgs/{org}/members", {"per_page": 100})

    if members_response.status_code == 200:

        try:
            last_page = int(members_response.links["last"]["url"].split("=")[-1])
        except KeyError:
            last_page = 1

        for i in range(0, last_page):
            members = gh.get(f"/orgs/{org}/members", {"per_page": 100, "page": i}).json()
        
            for member in members:
                org_members.append(member["login"])

        for pr in pulls_response.json():
            author = pr["user"]["login"]

            if author not in org_members:
                return True
            
        return False
    
    else:
        return f"Error {members_response.status_code}: {members_response.json()["message"]}"

# Any repos breaking naming conventions (uppercase, specials, etc.)
def check_breaks_naming(repo_name: str) -> bool | str:
    """
    Checks if the given repository name breaks naming convention.
    Returns True if breaks convention

    Args:
        repo_name (str): The name of the repository
    Returns:
        bool (True if check breaks policy)
    """
    for character in repo_name:
        if not(character.isnumeric() or character.isalpha() or character in ["_", "-"]) or character.isupper():
            return True
        
    return False


# Uses the above checks to get the repository data
def get_repository_data(gh: api_controller, org: str) -> list[dict] | str:
    """
    Gets all the repositories in the organisation and runs the policy checks on them.

    Args:
        gh (api_controller): An instance of the api_controller class to make calls to the GitHub API
        org (str): The name of the organisation
    Returns:
        list[dict] (A list of formatted repository data)
        or
        str (an error has occured when accessing the API)
    """
    repo_list = []

    repos_response = gh.get(f"/orgs/{org}/repos", {"per_page": 100})

    if repos_response.status_code == 200:
        try:
            last_page = int(repos_response.links["last"]["url"].split("=")[-1])
        except KeyError:
            # If Key Error, Last doesn't exist therefore 1 page
            last_page = 1

        for i in range(0, last_page):
            repos_response = gh.get(f"/orgs/{org}/repos", {"per_page": 100, "page": i+1})

            if repos_response.status_code == 200:
                repos = repos_response.json()

                for repo in repos:
                    repo_info = {
                        "name": repo["name"],
                        "type": repo["visibility"],
                        "url": repo["html_url"],
                        "checklist": {
                            "inactive": check_inactive(repo),
                            "unprotected_branches": check_branch_protection(repo["branches_url"].replace("{/branch}", ""), gh),
                            "unsigned_commits": check_signed_commits(repo["commits_url"].replace("{/sha}", ""), gh),
                            "readme_missing": check_file_exists(repo["contents_url"], gh, ["README.md", "readme.md"]),
                            "license_missing": check_file_exists(repo["contents_url"], gh, ["LICENSE.md", "LICENSE"]),
                            "pirr_missing": check_file_exists(repo["contents_url"], gh, ["PIRR.md"]),
                            "gitignore_missing": check_file_exists(repo["contents_url"], gh, [".gitignore"]),
                            "external_pr": check_external_pr(repo["pulls_url"].replace("{/number}", ""), repo["full_name"], gh),
                            "breaks_naming_convention": check_breaks_naming(repo["name"])
                        }
                    }

                    # If repo type is public, then PIRR check does not apply, so set to False
                    # If repo type is private/internal, then License check does not apply, so set to False
                    if repo_info["type"] == "public":
                        repo_info["checklist"]["pirr_missing"] = False
                    else:
                        repo_info["checklist"]["license_missing"] = False

                    repo_list.append(repo_info)

            else:
                return f"Error {repos_response.status_code}: {repos_response.json()["message"]}"

        return repo_list
    else:
        return f"Error {repos_response.status_code}: {repos_response.json()["message"]}"