import datetime
from dateutil.relativedelta import relativedelta

from api_interface import api_controller

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
    print("e")

# Repos with unsigned commits
def check_unsigned_commits(repo_api_url: str, gh: api_controller) -> bool | str:
    print("e")

# Repos without README.md, Liscense file (public only), 
# PIRR.md (private or internal) and .gitignore
def check_missing_files(repo_api_url: str, gh: api_controller) -> bool | str:
    print("e")

# Any external PR's
def check_external_pr(repo_api_url: str, gh: api_controller) -> bool | str:
    print("e")

# Any repos breaking naming conventions (uppercase, specials, etc.)
def check_naming(repo_api_url: str, gh: api_controller) -> bool | str:
    print("e")