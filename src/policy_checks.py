import datetime
from dateutil.relativedelta import relativedelta

from api_interface import api_controller

# User Checks

# Users with no ONS email in their account


# Check if org memebers should be there



# SLO Scripts

# Secret Scanning
# Alerts open > 5 days
def get_secret_scanning_alerts(gh: api_controller, org: str) -> list[dict] | str:
    secret_alerts_response = gh.get(f"https://api.github.com/orgs/{org}/secret-scanning/alerts", {"state": "open"}, False)

    if secret_alerts_response.status_code == 200:
        secret_alerts = secret_alerts_response.json()

        comparison_date = datetime.datetime.today() - datetime.timedelta(days=5)

        pop_count = 0

        # Remove all alerts openned < 5 days ago
        for i in range(0, len(secret_alerts)):
            date_openned = datetime.datetime.strptime(secret_alerts[i]["created_at"], "%Y-%m-%dT%H:%M:%SZ")

            if date_openned > comparison_date:
                secret_alerts.pop(i)
                pop_count += 1

        formatted_alerts = []

        for alert in secret_alerts:
            formatted_alert = {
                "repo": alert["repository"]["name"],
                "secret": f"{alert["secret_type_display_name"] - alert["secret"]}",
                "link": alert["html_url"]
            }

            formatted_alerts.append(formatted_alert)

        return formatted_alerts
    else:
        return f"Error {secret_alerts_response.status_code}: {secret_alerts_response.json()["message"]}"

# Dependabot
# Critical alerts open > 5 days


# High alerts oepn > 15 days


# Medium alerts open > 60 days


# Low alerts open > 90 days



# Repository Checks

# Repos not updated for > 1 yr
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

    comparison_date = datetime.datetime.today() - relativedelta(years=1)

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
    Checks if the last 15 commits are signed.
    If any commit is not signed, return True

    Args:
        repo_api_url (str): The API endpoint to get the repository's commits
        gh (api_controller): An instance of the api_controller class to make calls to the GitHub API
    Returns:
        bool (True if check breaks policy)
        or
        str (an error has occured when accessing the API)
    """

    commits_response = gh.get(repo_api_url, {"per_page": 15}, False)

    if commits_response.status_code == 200:
        commits = commits_response.json()

        unsigned_commits = False

        for commit in commits:
            if commit["commit"]["verification"]["verified"] == False:
                unsigned_commits = True

        return unsigned_commits

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