import datetime
from dateutil.relativedelta import relativedelta

from api_interface import api_controller

from pprint import pprint

# Users with no ONS email in their account


# Check if org memebers should be there


# SLOs (probably separate script)


# Repos not updated for > 1 yr
def check_inactive(repo_api_url: str, gh: api_controller) -> bool | str:
    response = gh.get(repo_api_url, {}, False)

    if response.status_code == 200:
        json = response.json()

        last_update = datetime.datetime.strptime(json["pushed_at"], "%Y-%m-%dT%H:%M:%SZ")

        comparison_date = datetime.datetime.today() - relativedelta(years=1)

        if last_update < comparison_date:
            return True
        else:
            return False

    else:
        return f"Error {response.status_code}: {response.json()["message"]}"

# Repos with no branch protection rules
def check_branch_protection(repo_api_url: str, gh: api_controller) -> bool | str:
    response = gh.get(repo_api_url, {}, False)

    if response.status_code == 200:
        json = response.json()

        branches_protected = True
        unprotected_branches = []

        for branch in json:
            if branch["protected"] == False:
                branches_protected = False

                unprotected_branches.append(branch["name"])

        return branches_protected

    else:
        return f"Error {response.status_code}: {response.json()["message"]}"

# Repos with unsigned commits
def check_signed_commits(repo_api_url: str, gh: api_controller) -> bool | str:
    response = gh.get(repo_api_url, {"per_page": 15}, False)

    if response.status_code == 200:
        json = response.json()

        commits_signed = True

        for commit in json:
            if commit["commit"]["verification"]["verified"] == False:
                commits_signed = False

        return commits_signed

    else:
        return f"Error {response.status_code}: {response.json()["message"]}"

# Repos without README.md, Liscense file (public only), 
# PIRR.md (private or internal) and .gitignore

def check_readme_exists(repo_api_url: str, gh: api_controller) -> bool | str:
    # Uppercase README.md
    readme_exists = True if gh.get(repo_api_url.replace("{+path}", "README.md"), {}, False).status_code == 200 else False

    # Lowercase readme.md
    readme_exists = (True if gh.get(repo_api_url.replace("{+path}", "readme.md"), {}, False).status_code == 200 else False) or readme_exists

    return readme_exists

# Repos without License file
def check_license_exists(repo_api_url: str, gh: api_controller) -> bool | str:
    # LICENSE.md
    license_exists = True if gh.get(repo_api_url.replace("{+path}", "LICENSE.md"), {}, False).status_code == 200 else False

    # LICENSE without .md
    license_exists = (True if gh.get(repo_api_url.replace("{+path}", "LICENSE"), {}, False).status_code == 200 else False) or license_exists

    return license_exists

# Repos without PIRR.md
def check_pirr_exists(repo_api_url: str, gh: api_controller) -> bool | str:
    pirr_exists = True if gh.get(repo_api_url.replace("{+path}", "PIRR.md"), {}, False).status_code == 200 else False

    return pirr_exists

# Repos without .gitignore
def check_gitignore_exists(repo_api_url: str, gh: api_controller) -> bool | str:
    gitignore_exists = True if gh.get(repo_api_url.replace("{+path}", ".gitignore"), {}, False).status_code == 200 else False

    return gitignore_exists

# Any external PR's
def check_external_pr(repo_api_url: str, repo_full_name: str, gh: api_controller) -> bool | str:
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


# Any repos breaking naming conventions (uppercase, specials, etc.)
def check_breaks_naming(repo_name: str) -> bool | str:
    for character in repo_name:
        if not(character.isnumeric() or character.isalpha() or character in ["_", "-"]) or character.isupper():
            return True
        
    return False