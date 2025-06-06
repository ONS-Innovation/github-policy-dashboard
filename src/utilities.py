"""A module containing utility functions for the dashboard."""

import streamlit as st
import os
import boto3
import github_api_toolkit
from datetime import timedelta
from requests import Response
from typing import Tuple

def get_environment_variables() -> dict:
    """
    Retrieves environment variables from the system.

    Returns:
        dict: A dictionary containing environment variables.
    """
    
    org = os.getenv("GITHUB_ORG")
    client_id = os.getenv("GITHUB_APP_CLIENT_ID")

    # AWS Secret Manager Secret Name for the .pem file
    secret_name = os.getenv("AWS_SECRET_NAME")
    secret_reigon = os.getenv("AWS_DEFAULT_REGION")

    account = os.getenv("AWS_ACCOUNT_NAME")
    bucket_name = f"{account}-policy-dashboard"

    return {
        "org": org,
        "client_id": client_id,
        "secret_name": secret_name,
        "secret_region": secret_reigon,
        "bucket_name": bucket_name
    }

def get_last_modified(s3: boto3.client, bucket: str, filename: str) -> str | None:
    """
    Retrieves the last modified date of a file in an S3 bucket.

    Args:
        bucket (str): The name of the S3 bucket.
        filename (str): The name of the file in the S3 bucket.

    Returns:
        str | None: The last modified date in "YYYY-MM-DD @ HH:MM" format, or None if not found.
    """

    response = s3.head_object(Bucket=bucket, Key=filename)
    
    last_modified = response['LastModified']

    if not last_modified:
        return None

    return last_modified.strftime("%Y-%m-%d @ %H:%M")

@st.cache_data(ttl=timedelta(minutes=30))
def get_ql_interface(_secret_manager, secret_name: str, org: str, client_id: str) -> github_api_toolkit.github_graphql_interface:
    """Retrieves a GraphQL interface for GitHub API using the provided secret manager and organization details.

    Args:
        _secret_manager (boto3.client): The AWS Secrets Manager client.
        secret_name (str): The name of the secret containing the GitHub App private key.
        org (str): The GitHub organization name.
        client_id (str): The GitHub App client ID.

    Returns:
        github_api_toolkit.github_graphql_interface: An instance of the GraphQL interface for GitHub API.
    """

    secret = _secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]
    token = github_api_toolkit.get_token_as_installation(org, secret, client_id)
    ql = github_api_toolkit.github_graphql_interface(token[0])

    return ql

def get_rest_interface(_secret_manager, secret_name: str, org: str, client_id: str) -> github_api_toolkit.github_interface:
    """Retrieves a REST interface for GitHub API using the provided secret manager and organization details.

    Args:
        _secret_manager (boto3.client): The AWS Secrets Manager client.
        secret_name (str): The name of the secret containing the GitHub App private key.
        org (str): The GitHub organization name.
        client_id (str): The GitHub App client ID.

    Returns:
        github_api_toolkit.github_interface: An instance of the REST interface for GitHub API.
    """

    secret = _secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]
    token = github_api_toolkit.get_token_as_installation(org, secret, client_id)
    rest = github_api_toolkit.github_interface(token[0])

    return rest

@st.cache_data(ttl=timedelta(hours=1))
def get_github_repository_information(
    _rest: github_api_toolkit.github_interface, 
    org: str, 
    repository_list: list = None
) -> Tuple[dict, dict]:
    """Retrieves additional information about repositories in a GitHub organization (Repository Type and Archived Status).

    Args:
        ql (github_api_toolkit.github_graphql_interface): The GraphQL interface for GitHub API.
        org (str): The GitHub organization name.
        repository_list (list, optional): A list of specific repositories to check. If None, all repositories in the organization are checked.

    Returns:
        Tuple[dict, dict]: A tuple containing two dictionaries:
            - repo_types: A dictionary mapping repository names to their types (Public, Internal, Private).
            - archived_status: A dictionary mapping repository names to their archived status (Archived, Not Archived).
    """

    if repository_list:
        # If a specific list of repositories is provided, retrieve their types
        # This is useful since Secret Scanning will only return a handful of repositories

        repo_types = {}
        archived_status = {}

        for repo in repository_list:
            response = _rest.get(f"/repos/{org}/{repo}")

            if type(response) is not Response:
                print(f"Error retrieving repository {repo}: {response}")
                repo_types[repo] = "Unknown"
                archived_status[repo] = "Unknown"
            else:
                repository = response.json()
                repository_type = repository.get("visibility", "Unknown").title()
                repo_types[repo] = repository_type

                archived_status[repo] = "Archived" if repository.get("archived", False) else "Not Archived"

    else:
        # If no specific list is provided, retrieve all repositories in the organization
        # This is useful for Dependabot Alerts where there are many repositories
        # There will be less API calls doing 100 repositories at a time than each repository individually

        repo_types = {}
        archived_status = {}
        repository_list = []

        response = _rest.get(f"/orgs/{org}/repos", params={"per_page": 100})

        if type(response) is not Response:
            print(f"Error retrieving repositories: {response}")
            return repo_types, archived_status
        else:
            try:
                last_page = int(response.links["last"]["url"].split("=")[-1])
            except KeyError:
                last_page = 1

        for page in range(1, last_page + 1):
            response = _rest.get(f"/orgs/{org}/repos", params={"per_page": 100, "page": page})

            if type(response) is not Response:
                print(f"Error retrieving repositories on page {page}: {response}")
                continue

            repositories = response.json()

            repository_list = repository_list + repositories

        for repo in repository_list:
            repository_name = repo.get("name")
            repository_type = repo.get("visibility", "Unknown").title()
            repo_types[repository_name] = repository_type

            archived_status[repository_name] = "Archived" if repo.get("archived", False) else "Not Archived"
    
    return repo_types, archived_status
