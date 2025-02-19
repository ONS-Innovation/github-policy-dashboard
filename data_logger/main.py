from typing import Any, Tuple, Callable, TypeVar, ParamSpec
import os
import json
import time
from functools import wraps
import boto3
from requests import Response
from pprint import pprint
import datetime

import github_api_toolkit

import custom_threading
from logger import wrapped_logging
import policy_checks


T = TypeVar("T")
P = ParamSpec("P")

def get_config_file(path: str) -> Any:
    """Loads a configuration file as a dictionary.
    Args:
        path (str): The path to the configuration file.
    Raises:
        Exception: If the configuration file is not found.
    Returns:
        Any: The configuration file as a dictionary.
    """
    try:
        with open(path) as f:
            config = json.load(f)
    except FileNotFoundError:
        error_message = f"{path} configuration file not found. Please check the path."
        raise Exception(error_message) from None

    if type(config) is not dict:
        error_message = f"{path} configuration file is not a dictionary. Please check the file contents."
        raise Exception(error_message)

    return config


def get_dict_value(dictionary: dict, key: str) -> Any:
    """Gets a value from a dictionary and raises an exception if it is not found.
    Args:
        dictionary (dict): The dictionary to get the value from.
        key (str): The key to get the value for.
    Raises:
        Exception: If the key is not found in the dictionary.
    Returns:
        Any: The value of the key in the dictionary.
    """
    value = dictionary.get(key)

    if value is None:
        raise Exception(f"Key {key} not found in the dictionary.")

    return value


def get_environment_variable(variable_name: str) -> str:
    """Gets an environment variable and raises an exception if it is not found.
    Args:
        variable_name (str): The name of the environment variable to get.
    Raises:
        Exception: If the environment variable is not found.
    Returns:
        str: The value of the environment variable.
    """
    variable = os.getenv(variable_name)

    if variable is None:
        error_message = f"{variable_name} environment variable not found. Please check your environment variables."
        raise Exception(error_message)

    return variable


def get_environment_variables() -> Tuple[str, str, str, str, str]:
    """Gets the environment variables needed for the script.
    Raises:
        Exception: If any of the environment variables are not found.
    Returns:
        Tuple[str, str, str, str, str]: The environment variables.
    """
    org = get_environment_variable("GITHUB_ORG")
    app_client_id = get_environment_variable("GITHUB_APP_CLIENT_ID")
    aws_default_region = get_environment_variable("AWS_DEFAULT_REGION")
    aws_secret_name = get_environment_variable("AWS_SECRET_NAME")
    aws_account_name = get_environment_variable("AWS_ACCOUNT_NAME")

    return org, app_client_id, aws_default_region, aws_secret_name, aws_account_name


def get_access_token(secret_manager: Any, secret_name: str, org: str, app_client_id: str) -> Tuple[str, str]:
    """Gets the access token from the AWS Secret Manager.
    Args:
        secret_manager (Any): The Boto3 Secret Manager client.
        secret_name (str): The name of the secret to get.
        org (str): The name of the GitHub organization.
        app_client_id (str): The client ID of the GitHub App.
    Raises:
        Exception: If the secret is not found in the Secret Manager.
    Returns:
        str: The access token.
    """
    response = secret_manager.get_secret_value(SecretId=secret_name)

    pem_contents = response.get("SecretString", "")

    if not pem_contents:
        error_message = (
            f"Secret {secret_name} not found in AWS Secret Manager. Please check your environment variables."
        )
        raise Exception(error_message)

    token = github_api_toolkit.get_token_as_installation(org, pem_contents, app_client_id)

    if type(token) is not tuple:
        raise Exception(token)

    return token


def retry_on_error(max_retries: int = 3, delay: int = 2) -> Any:
    """A decorator that retries a function if an exception is raised.
    Args:
        max_retries (int, optional): The number of times the function should be retried before failing. Defaults to 3.
        delay (int, optional): The time delay in seconds between retry attempts. Defaults to 2.
    Raises:
        Exception: If the function fails after the maximum number of retries.
    Returns:
        Any: The result of the function.
    """

    def decorator(func: Callable[P, T]) -> Any:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any | None:
            retries = 0

            logger = wrapped_logging(False)

            while retries < max_retries:
                try:
                    result = func(*args, **kwargs)
                    if result is not None:  # Check if request was successful
                        return result
                    raise Exception("Request failed with None result")
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        raise Exception(e) from e
                    logger.log_warning(f"Attempt {retries} failed. Retrying in {delay} seconds...")
                    time.sleep(delay)
            return None

        return wrapper

    return decorator

@retry_on_error()
def get_repository_page(
        logger: wrapped_logging,
        ql: github_api_toolkit.github_graphql_interface,
        org: str,
        max_repos: int,
        cursor: str = None,
) -> Any:
    
    query = """
    query($org: String!, $max_repos: Int!, $cursor: String) {
        organization(login: $org) {
            repositories(first: $max_repos, after: $cursor, isArchived: false) {
                pageInfo {
                    endCursor
                    hasNextPage
                }
                nodes {
                    name
                    visibility
                    url
                    createdAt
                    pushedAt

                    # Checks if dependabot is enabled
                    hasVulnerabilityAlertsEnabled

                    # Checks for Signed Commits, External Pull Requests and Repository Contents have been moved to separate functions
                    # This is to reduce the complexity of the query, allow for threading and reduce GitHub API Errors.

                    # Currently, GraphQL does not support:
                    # - Checking if Secret Scanning is enabled
                    # - Seeing if a branch is protected (from an organization level)
                    #
                    # These will need to be checked using the REST API
                    # Along with the CODEOWNERS checks
                }
            }
        }
    }
    """

    variables = {
        "org": org,
        "max_repos": max_repos,
        "cursor": cursor,
    }

    response = ql.make_ql_request(query, variables)

    response.raise_for_status()

    logger.log_info(f"Request successful. Response Status Code: {response.status_code}")

    return response.json()


def clean_repositories(repositories: list[dict]) -> list[dict]:
    """Removes any None values from a list of repositories.

    Args:
        repositories (list[dict]): A list of repositories.

    Returns:
        list[dict]: The list of repositories with None values removed.
    """
    return [repository for repository in repositories if repository is not None]


def log_error_repositories(logger: wrapped_logging, response_json: dict) -> None:
    """Logs any errors in the response from the GitHub API.

    Args:
        logger (wrapped_logging): The logger object.
        response_json (dict): The response from the GitHub API.
    """
    error_repositories = response_json.get("errors")

    if error_repositories is not None:
        logger.log_error(f"Error repositories: {error_repositories}")


def filter_response(logger: wrapped_logging, response_json: dict) -> Any:
    """Filters the response from the GitHub API to get the repositories.

    Args:
        logger (wrapped_logging): The logger object.
        response_json (dict): The response from the GitHub API.

    Returns:
        list[dict]: The list of repositories.
    """
    response_repositories = response_json["data"]["organization"]["repositories"]["nodes"]

    response_repositories = clean_repositories(response_repositories)

    log_error_repositories(logger, response_json)

    return response_repositories


def get_repositories(
    logger: wrapped_logging, ql: github_api_toolkit.github_graphql_interface, org: str,
) -> tuple[list[dict], int]:
    """Gets all the repositories from a GitHub organization.

    Args:
        logger (wrapped_logging): The logger object.
        ql (github_api_toolkit.github_graphql_interface): The GraphQL interface for the GitHub API.
        org (str): The name of the GitHub organization.

    Returns:
        tuple[list[dict], int]: A tuple containing the list of repositories and the number of pages of repositories.
    """
    repositories = []
    number_of_pages = 1

    response_json = get_repository_page(logger, ql, org, 100)

    response_repositories = filter_response(logger, response_json)

    repositories.extend(response_repositories)

    while response_json["data"]["organization"]["repositories"]["pageInfo"]["hasNextPage"]:
        cursor = response_json["data"]["organization"]["repositories"]["pageInfo"]["endCursor"]

        logger.log_info(f"Getting page {number_of_pages + 1} with cursor {cursor}.")

        response_json = get_repository_page(logger, ql, org, 100, cursor)

        response_repositories = filter_response(logger, response_json)

        repositories.extend(response_repositories)

        number_of_pages += 1

    return repositories, number_of_pages


def get_rest_data(logger: wrapped_logging, rest: github_api_toolkit.github_interface, org: str, repository: str) -> dict:
    """Gets the REST data for a repository (branch protection and secret scanning).

    Args:
        logger (wrapped_logging): The logger object.
        rest (github_api_toolkit.github_interface): The REST interface for the GitHub API.
        org (str): The name of the GitHub organization.
        repository (str): The name of the repository.

    Raises:
        Exception: If the response from the GitHub API is not a Response object (Request failed).

    Returns:
        dict: The REST data for the repository.
    """

    checks = {}

    logger.log_info(f"Getting REST data for {repository}.")

    # Get Branch Protection

    response = rest.get(f"/repos/{org}/{repository}/branches")

    if type(response) is not Response:
        raise Exception(response)
    
    response_json = response.json()
    
    branch_protection = True

    for branch in response_json:
        protected = branch.get("protected", False)

        if not protected:
            branch_protection = False
            break
        
    checks["branch_protection"] = branch_protection

    # Get Secret Scanning

    response = rest.get(f"/repos/{org}/{repository}")

    if type(response) is not Response:
        raise Exception(response)
    
    response_json = response.json()

    secret_scanning = True

    if response_json["visibility"] == "public":
        if response_json["security_and_analysis"]["secret_scanning"]["status"] == "disabled":
            secret_scanning = False

    checks["secret_scanning"] = secret_scanning

    logger.log_info(f"REST data for {repository} retrieved.")

    return checks


def get_org_members(logger: wrapped_logging, rest: github_api_toolkit.github_interface, org: str) -> list[str]:
    """Gets the members of a GitHub organization.

    Args:
        logger (wrapped_logging): The logger object.
        rest (github_api_toolkit.github_interface): The REST interface for the GitHub API.
        org (str): The name of the GitHub organization.

    Raises:
        Exception: If the response from the GitHub API is not a Response object (Request failed).

    Returns:
        list[str]: The members of the GitHub organization.
    """

    members = []

    logger.log_info("Getting organisation members.")

    response = rest.get(f"/orgs/{org}/members", params={"per_page": 100})

    if type(response) is not Response:
        raise Exception(response)

    try:
        last_page = int(response.links["last"]["url"].split("=")[-1])
    except KeyError:
        last_page = 1

    logger.log_info(f"{last_page} pages of members to retrieve.")

    for page in range(1, last_page + 1):

        response = rest.get(f"/orgs/{org}/members", params={"per_page": 100, "page": page})

        if type(response) is not Response:
            raise Exception(response)

        response_json = response.json()

        for member in response_json:
            members.append(member["login"])

    logger.log_info(f"{len(members)} organisation members retrieved.")

    return members


def calculate_threading_groups(total_repos: int, number_of_threads: int) -> list[tuple[int, int]]:
    """Calculates the threading groups for processing repositories.

    Args:
        total_repos (int): The total number of repositories.
        number_of_threads (int): The number of threads to use.

    Returns:
        list[tuple[int, int]]: The threading groups for processing repositories (start, end).
    """

    batch_size = total_repos // number_of_threads
    remainder = total_repos % number_of_threads

    threading_groups = []

    start = 0

    for i in range(number_of_threads):
        
        end = start + batch_size

        if i == number_of_threads - 1:
            end += remainder

        threading_groups.append((start, end))

        start = end

    return threading_groups


@retry_on_error()
def get_remaining_data(ql: github_api_toolkit.github_graphql_interface, org: str, repository: str, max_commits: int) -> tuple[list[dict], list[dict], list[dict]]:
    """Gets the remaining data for a repository (signed commits, external PRs, repository contents).
    
    Args:
        ql (github_api_toolkit.github_graphql_interface): The GraphQL interface for the GitHub API.
        org (str): The name of the GitHub organization.
        repository (str): The name of the repository.
        max_commits (int): The maximum number of commits to get.

    Raises:
        Exception: If the response from the GitHub API is not a Response object (Request failed).

    Returns:
        tuple[list[dict], list[dict], list[dict]]: The remaining data for the repository (signed commits, external PRs, repository contents).
    """

    query = """
    query($org: String!, $repo: String!, $max_commits: Int!) {
        repository(owner: $org, name: $repo) {
            
            # Signed Commits
            
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: $max_commits) {
                            nodes {
                                signature {
                                    isValid
                                }
                            }
                        }
                    }
                }
            }

            # External PR

            pullRequests(first: 50, states: OPEN) {
                nodes {
                    author {
                        login
                    }
                }
            }

            # Contents

            object(expression: "HEAD:") {
                ... on Tree {
                    entries {
                        name
                    }
                }
            }
        }
    }
    """

    variables = {
        "org": org,
        "repo": repository,
        "max_commits": max_commits
    }

    response = ql.make_ql_request(query, variables)

    if type(response) is not Response:
        raise Exception(response)

    response_json = response.json()

    # Turn the respective data into a list of commits, pull requests and contents
    # If an error occurs, return an empty list
    try:
        commits = response_json["data"]["repository"]["defaultBranchRef"]["target"]["history"]["nodes"]
    except TypeError:
        commits = []

    try:
        pull_requests = response_json["data"]["repository"]["pullRequests"]["nodes"]
    except Exception:
        pull_requests = []

    try:
        contents = response_json["data"]["repository"]["object"]["entries"]
    except TypeError:
        contents = []

    return commits, pull_requests, contents


def get_repository_batch(logger: wrapped_logging, rest: github_api_toolkit.github_interface, ql: github_api_toolkit.github_graphql_interface, org: str, repositories: list[dict], org_members: list[str], inactivity_threshold: int, max_commits: int, start: int, end: int) -> list[dict]:
    """Processes a batch of repositories.

    Args:
        logger (wrapped_logging): The logger object.
        rest (github_api_toolkit.github_interface): The REST interface for the GitHub API.
        ql (github_api_toolkit.github_graphql_interface): The GraphQL interface for the GitHub API.
        org (str): The name of the GitHub organization.
        repositories (list[dict]): The list of repositories.
        org_members (list[str]): The members of the GitHub organization.
        inactivity_threshold (int): The inactivity threshold for a repository to be considered inactive.
        max_commits (int): The maximum number of commits to get for the signed commits check.
        start (int): The start index of the batch.
        end (int): The end index of the batch.

    Returns:
        list[dict]: The processed repositories in the batch.
    """

    output = []

    logger.log_info(f"Processing repositories {start} to {end}.")

    for i in range(start, end):
        repository = repositories[i]

        # Get outstanding QL Data (Signed Commits, External PRs and Repository Contents)
        commits, pull_requests, repository_contents = get_remaining_data(ql, org, repository["name"], max_commits)

        # Get REST Data (Branch Protection, Secret Scanning)

        rest_data = get_rest_data(logger, rest, org, repository["name"])

        # Get Codeowners and Point of Contact

        codeowners_path = ""
        codeowners_missing = policy_checks.file_missing(repository_contents, "CODEOWNERS")
        point_of_contact_missing = True

        if not codeowners_missing:
            codeowners_path = "CODEOWNERS"

        # If a CODEOWNERS is not found in the root directory, check the .github directory
        if codeowners_missing and not policy_checks.file_missing(repository_contents, ".github"):

            if ql.get_file_contents_from_repo(org, repository["name"], ".github/CODEOWNERS") != "File not Found.":
                codeowners_missing = False
                codeowners_path = ".github/CODEOWNERS"


        # If a CODEOWNERS file is found, check if there is a point of contact
        if not codeowners_missing:
            
            contents = ql.get_file_contents_from_repo(org, repository["name"], codeowners_path)
            codeowners = ql.get_codeowners_from_text(contents)
            codeowners = ql.identify_teams_and_users(codeowners)
            codeowners = ql.get_codeowner_users(org, codeowners)
            emails = ql.get_codeowner_emails(codeowners, org)

            if emails:
                point_of_contact_missing = False


        repository_data = {
            "name": repository["name"],
            "type": repository["visibility"],
            "url": repository["url"],
            "created_at": repository["createdAt"],
            "checklist": {
                "inactive": policy_checks.is_inactive(repository["pushedAt"], inactivity_threshold),
                "unprotected_branches": not rest_data["branch_protection"],
                "unsigned_commits": policy_checks.has_unsigned_commits(commits),
                "readme_missing": policy_checks.file_missing(repository_contents, "README.md"),
                "license_missing": policy_checks.file_missing(repository_contents, "LICENSE"),
                "pirr_missing": policy_checks.file_missing(repository_contents, "PIRR.md"),
                "gitignore_missing": policy_checks.file_missing(repository_contents, ".gitignore"),
                "external_pr": policy_checks.has_external_pr(pull_requests, org_members),
                "breaks_naming_convention": policy_checks.breaks_naming_convention(repository["name"]),
                "secret_scanning_disabled": not rest_data["secret_scanning"],
                "dependabot_disabled": not repository["hasVulnerabilityAlertsEnabled"],
                "codeowners_missing": codeowners_missing,
                "point_of_contact_missing": point_of_contact_missing
            }
        }

        # If the repository is public, the PIRR.md file is not required
        # If the repository is private, the LICENSE file is not required
        if repository["visibility"] == "PUBLIC":
            repository_data["checklist"]["pirr_missing"] = False
        else:
            repository_data["checklist"]["license_missing"] = False

        output.append(repository_data)

    return output


def get_output_data(logger: wrapped_logging, rest: github_api_toolkit.github_interface, ql: github_api_toolkit.github_graphql_interface, org: str, repositories: list[dict], inactivity_threshold: int, signed_commit_number: int, thread_count: int) -> list[dict]:
    """Gets the output data for all the repositories.

    Args:
        logger (wrapped_logging): The logger object.
        rest (github_api_toolkit.github_interface): The REST interface for the GitHub API.
        ql (github_api_toolkit.github_graphql_interface): The GraphQL interface for the GitHub API.
        org (str): The name of the GitHub organization.
        repositories (list[dict]): The list of repositories.
        inactivity_threshold (int): The inactivity threshold for a repository to be considered inactive.
        signed_commit_number (int): The maximum number of commits to get for the signed commits check.
        thread_count (int): The number of threads to use.

    Returns:
        list[dict]: The output data for all the repositories.
    """

    output = []

    org_members = get_org_members(logger, rest, org)

    threading_groups = calculate_threading_groups(len(repositories), thread_count)

    logger.log_info(f"Threading groups: {threading_groups}")

    threads = []

    for group in threading_groups:
        
        start, end = group

        thread = custom_threading.CustomThread(target=get_repository_batch, args=(logger, rest, ql, org, repositories, org_members, inactivity_threshold, signed_commit_number, start, end))

        threads.append(thread)

        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

        logger.log_info(f"{thread.name} processed {len(thread.return_value)} repositories.")

        output.extend(thread.return_value)

    logger.log_info(f"Processed {len(output)} repositories.")

    return output


def save_information(write_to_s3: bool, filename: str, data: Any, s3: boto3.client = None, bucket_name: str = None):
    """Saves information to a file.

    Args:
        write_to_s3 (bool): Whether to write the information to S3 or locally.
        filename (str): The name of the file to save the information to.
        data (Any): The data to save (JSON ONLY).
        s3 (boto3.client, optional): The S3 Client. Defaults to None.
        bucket_name (str, optional): The name of the S3 bucket to write to. Defaults to None.

    Raises:
        Exception: If the S3 client and bucket name are not provided when writing to S3.
    """

    if write_to_s3:

        if not s3 or not bucket_name:
            raise Exception("S3 client and bucket name required to write to S3.")
        
        s3.put_object(Bucket=bucket_name, Key=filename, Body=json.dumps(data, indent=4))

        logger.log_info(f"{filename} uploaded to S3.")

    else:

        # Check if ./output directory exists
        if not os.path.exists("./output"):
            os.makedirs("./output")

        # Write the data to a file locally
        filename = f"./output/{filename}"

        with open(filename, "w") as f:
            f.write(json.dumps(data, indent=4))

        logger.log_info(f"{filename} written locally.")


def process_dependabot_alerts(response_json: dict, threshold: int) -> list[dict]:
    """Processes the given dependabot alerts. Checks each alert against the threshold and formats the data.

    Args:
        response_json (dict): The dependabot response JSON from the GitHub API.
        threshold (int): The number of days an alert has been open for before it is considered a problem.

    Returns:
        list[dict]: The formatted dependabot alerts.
    """

    dependabot_data = []

    for alert in response_json:

        days_open = datetime.datetime.now() - datetime.datetime.strptime(alert["created_at"], "%Y-%m-%dT%H:%M:%SZ")

        days_open = days_open.days

        if (days_open > threshold):

            formatted_alert = {
                "repository": alert["repository"]["name"],
                "repository_url": alert["repository"]["html_url"],
                "created_at": alert["created_at"],
                "severity": alert["security_advisory"]["severity"]
            }

            dependabot_data.append(formatted_alert)

    return dependabot_data

def get_dependabot_data_for_severity(rest: github_api_toolkit.github_interface, org: str, severity: str, threshold: int) -> list[dict]:
    """Gets the Dependabot data for all the repositories in an organization.

    Args:
        logger (wrapped_logging): The logger object.
        rest (github_api_toolkit.github_interface): The REST interface for the GitHub API.
        org (str): The name of the GitHub organization.
        severity (str): The severity of the Dependabot alerts to get.
        threshold (int): The number of days an alert has been open for before it is considered a problem.

    Returns:
        list[dict]: The Dependabot data for all the repositories in the organization.
    """

    dependabot_data = []

    # Get the threshold for the given severity


    response = rest.get(f"/orgs/{org}/dependabot/alerts", {"state": "open", "severity": severity, "per_page": 100})

    if type(response) is not Response:
        raise Exception(response)

    try:
        last_page = int(response.links["last"]["url"].split("=")[-1])
    except KeyError:
        last_page = 1

    for page in range(1, last_page + 1):
        response = rest.get(f"/orgs/{org}/dependabot/alerts", {"state": "open", "per_page": 100, "severity": severity, "page": page})

        if type(response) is not Response:
            raise Exception(response)
        
        response_json = response.json()

        response_json = process_dependabot_alerts(response_json, threshold)

        dependabot_data.extend(response_json)

    return dependabot_data


def get_dependabot_data(rest: github_api_toolkit.github_interface, org: str, dependabot_thresholds: dict) -> list[dict]:
    """Gets the Dependabot data for all the repositories in an organization.

    Args:
        rest (github_api_toolkit.github_interface): The REST interface for the GitHub API.
        org (str): The name of the GitHub organization.
        dependabot_thresholds (dict): The thresholds for the Dependabot alerts from config.json.

    Returns:
        list[dict]: The Dependabot data for all the repositories in the organization.
    """

    dependabot_data = []

    severities = dependabot_thresholds.keys()

    threads = []

    for severity in severities:

        threshold = dependabot_thresholds[severity]

        thread = custom_threading.CustomThread(target=get_dependabot_data_for_severity, args=(rest, org, severity, threshold))

        threads.append(thread)

        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

        logger.log_info(f"{thread.name} processed {len(thread.return_value)} alerts.")

        dependabot_data.extend(thread.return_value)

    return dependabot_data


def group_dependabot_data(dependabot_data: list[dict]) -> dict:

    grouped_data = {}

    for alert in dependabot_data:
        
        repository = alert["repository"]

        ## TODO: Skip archived repositories

        if repository not in grouped_data:
            grouped_data[repository] = {
                "url": alert["repository_url"],
                "oldest_alert": 0,
                "worst_severity": "none",
                "alerts": {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0
                }
            }

        match alert["severity"]:
            case "critical":
                grouped_data[repository]["alerts"]["critical"] += 1
            case "high":
                grouped_data[repository]["alerts"]["high"] += 1
            case "medium":
                grouped_data[repository]["alerts"]["medium"] += 1
            case "low":
                grouped_data[repository]["alerts"]["low"] += 1

        ## TODO: Update the oldest alert (days) and worst severity

    return grouped_data


start_time = time.time()

# Load the configuration file

config_file_path = "./data_logger/config/config.json"
config = get_config_file(config_file_path)

features = get_dict_value(config, "features")
settings = get_dict_value(config, "settings")

# Initialise logging

debug = get_dict_value(features, "show_log_locally")

logger = wrapped_logging(debug)

logger.log_info("Logger initialised.")

# Get the environment variables

org, app_client_id, aws_default_region, aws_secret_name, aws_account_name = get_environment_variables()

## Calculate the S3 bucket information

bucket_name = f"{aws_account_name}-policy-dashboard"

logger.log_info("Environment variables loaded.")

# Create Boto3 clients

session = boto3.session.Session()

## S3

s3 = session.client("s3")

logger.log_info("S3 client created.")

## Secret Manager

secret_manager = session.client(service_name="secretsmanager", region_name=aws_default_region)

logger.log_info("Secret Manager client created.")

# Setup API Interfaces (REST and GraphQL)

token = get_access_token(secret_manager, aws_secret_name, org, app_client_id)

ql = github_api_toolkit.github_graphql_interface(token[0])
rest = github_api_toolkit.github_interface(token[0])

logger.log_info("API interfaces created.")

# # Dev code to check GitHub Rate Limit
# rate_limit = rest.get("/rate_limit").json()
# pprint(rate_limit)
# quit()

# Initialise time variables

repository_time = 0
dependabot_time = 0
secret_scanning_time = 0

# Get write_to_s3 from the configuration file

write_to_s3 = get_dict_value(features, "write_to_s3")


# Get a list of non-archived repositories in the organization

## This list is used to get repository information, dependabot information, and secret scanning information
## This is so alerts for archived repositories are not collected
## This also allows information collection to be modular and toggleable through config.json

repositories, number_of_pages = get_repositories(logger, ql, org)


# Get Repository Information
## Get, Process, and Store Repository Information

repository_collection = get_dict_value(features, "repository_collection")

if repository_collection:

    repository_start_time = time.time()

    logger.log_info("Repository collection enabled. Collecting repository data.")

    thread_count = get_dict_value(settings, "thread_count")
    inactivity_threshold = get_dict_value(settings, "inactivity_threshold")
    signed_commit_number = get_dict_value(settings, "signed_commit_number")

    # Get the remaining data for the repositories and format it appropriately
    repository_data = get_output_data(logger, rest, ql, org, repositories, inactivity_threshold, signed_commit_number, thread_count)

    logger.log_info(f"Taken {time.time() - repository_start_time} seconds repository information.")

    # Upload Repository Data to S3

    save_information(write_to_s3, "repositories.json", repository_data, s3, bucket_name)

    repository_time = time.time() - repository_start_time

else:
    logger.log_info("Repository collection disabled. Skipping repository data collection.")

# Get Dependabot Information
## Get, Process, and Store Dependabot Information

dependabot_collection = get_dict_value(features, "dependabot_collection")

if dependabot_collection:

    dependabot_start_time = time.time()

    logger.log_info("Dependabot collection enabled. Collecting Dependabot data.")

    # Get Dependabot Thresholds
    dependabot_thresholds = get_dict_value(settings, "dependabot_thresholds")

    # Get Dependabot Data

    dependabot_data = get_dependabot_data(rest, org, dependabot_thresholds)

    logger.log_info(f"Taken {time.time() - dependabot_start_time} seconds to collect Dependabot data.")

    # Group the data by repository and remove archived repositories

    dependabot_data = group_dependabot_data(dependabot_data)

    # Upload Dependabot Data to S3

    save_information(write_to_s3, "dependabot.json", dependabot_data, s3, bucket_name)

    dependabot_time = time.time() - dependabot_start_time

else:
    logger.log_info("Dependabot collection disabled. Skipping Dependabot data collection.")

# Get Secret Scanning Information
## Get, Process, and Store Secret Scanning Information

secret_scanning_collection = get_dict_value(features, "secret_scanning_collection")

if secret_scanning_collection:
    
    secret_scanning_start_time = time.time()

    logger.log_info("Secret Scanning collection enabled. Collecting Secret Scanning data.")

    # Get Secret Scanning Data

    secret_scanning_data = []

    logger.log_info(f"Taken {time.time() - secret_scanning_start_time} seconds to collect Secret Scanning data.")

    # Upload Secret Scanning Data to S3

    save_information(write_to_s3, "secret_scanning.json", secret_scanning_data, s3, bucket_name)

    secret_scanning_time = time.time() - secret_scanning_start_time

else:
    logger.log_info("Secret Scanning collection disabled. Skipping Secret Scanning data collection.")

end_time = time.time()

logger.log_info(f"Script took {end_time - start_time} seconds to run.")
logger.log_info(f"Repository collection took {repository_time} seconds.")
logger.log_info(f"Dependabot collection took {dependabot_time} seconds.")
logger.log_info(f"Secret Scanning collection took {secret_scanning_time} seconds.")

def handler(event, context) -> str: # type: ignore[no-untyped-def]

    return "Hello, World!"