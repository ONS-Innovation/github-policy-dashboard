"""A list of policy related checks for the data logger."""

import datetime
from dateutil.relativedelta import relativedelta

def is_inactive(last_update: str, threshold: int) -> bool:
    """Check if the last update is older than the threshold.

    Args:
        last_update (str): When the data was last updated.
        threshold (int): The number of years to check against.

    Returns:
        bool: True if the data is older than the threshold, False otherwise.
    """

    update_date = datetime.datetime.strptime(last_update, "%Y-%m-%dT%H:%M:%SZ")
    threshold_date = datetime.datetime.today() - relativedelta(years=threshold)

    return update_date < threshold_date

def has_unsigned_commits(commits: list) -> bool:
    """Check if the commits contain unsigned commits.

    Args:
        commits (list): A list of commits.

    Returns:
        bool: True if the commits contain unsigned commits, False otherwise.
    """

    for commit in commits:
        if commit["signature"] == None:
            return True

    return False


def file_missing(file_list: list[str], filename: str) -> bool:
    """Check if the file is missing from the file list.

    Args:
        file_list (list[str]): A list of files.
        filename (str): The file to check.

    Returns:
        bool: True if the file is missing, False otherwise.
    """

    for file in file_list:
        if file["name"] == filename:
            return False
    
    return True


def has_external_pr(prs: list, org_members: list) -> bool:
    """Check if the PRs contain external PRs.

    Args:
        prs (list): A list of PRs.
        org_members (list): A list of organization members.

    Returns:
        bool: True if the PRs contain external PRs, False otherwise.
    """

    for pr in prs:
        # Dependabot PRs are not considered external
        if pr["author"]["login"] == "dependabot[bot]":
            continue

        if pr["author"]["login"] not in org_members:
            return True

    return False


def breaks_naming_convention(name: str) -> bool:
    """Check if the name breaks the naming convention.

    Args:
        name (str): The name to check.

    Returns:
        bool: True if the name breaks the naming convention, False otherwise.
    """

    for character in name:
        if not (character.isnumeric() or character.isalpha() or character in ["_", "-"]) or character.isupper():
            return True
        
    return False