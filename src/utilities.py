"""A module containing utility functions for the dashboard."""

import streamlit as st
import os
import boto3
import github_api_toolkit
from datetime import timedelta

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
