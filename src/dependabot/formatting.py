"""A module to format dependabot data for the dashboard."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import boto3

from utilities import get_rest_interface, get_github_repository_information

@st.cache_data(ttl=timedelta(hours=1))
def add_repository_information(
    df_dependabot: pd.DataFrame,
    _secret_manager: boto3.client,
    secret_name: str,
    org: str,
    client_id: str,
) -> pd.DataFrame:
    """Add additional repository information to the secret scanning DataFrame.

    Args:
        df_dependabot (pd.DataFrame): The DataFrame containing dependabot data.
        _secret_manager (boto3.client): A Boto3 Secrets Manager client to interact with AWS Secrets Manager.
        secret_name (str): The name of the secret containing the GitHub App private key.
        org (str): The GitHub organization name.
        client_id (str): The GitHub App client ID.

    Returns:
        pd.DataFrame: A DataFrame with an additional column for repository type.
    """
    
    rest = get_rest_interface(
        _secret_manager=_secret_manager,
        secret_name=secret_name,
        org=org,
        client_id=client_id,
    )

    repo_types, archived_status = get_github_repository_information(
        _rest=rest,
        org=org,
    )

    # Add a new column for repository type
    df_dependabot["Repository Type"] = df_dependabot["Repository"].map(repo_types)

    # Add a new column for archived status
    df_dependabot["Archived Status"] = df_dependabot["Repository"].map(archived_status)

    return df_dependabot

def filter_dependabot(
        df_dependabot: pd.DataFrame, 
        start_date: pd.Timestamp, 
        end_date: pd.Timestamp, 
        severities_to_exclude: list,
        types_to_exclude: list,
        archived_status: str,
    ) -> pd.DataFrame:
    """Filter dependabot data based on user inputs.

    Args:
        df_dependabot (pd.DataFrame): The DataFrame containing dependabot data.
        start_date (pd.Timestamp): The start date for filtering.
        end_date (pd.Timestamp): The end date for filtering.
        severities_to_exclude (list): The list of severities to exclude from the DataFrame.
        types_to_exclude (list): The list of repository types to exclude from the DataFrame.
        archived_status (str): The archived status to filter by. Options are "All", "Archived", or "Not Archived".

    Returns:
        pd.DataFrame: A DataFrame filtered by the specified date range, severities, and repository types.
    """

    df_dependabot = df_dependabot.loc[
        (df_dependabot["Creation Date"] >= pd.to_datetime(start_date))
        & (df_dependabot["Creation Date"] <= pd.to_datetime(end_date))
    ]

    for severity in severities_to_exclude:
        df_dependabot = df_dependabot[df_dependabot["Severity"] != severity]

    for repo_type in types_to_exclude:
        df_dependabot = df_dependabot[df_dependabot["Repository Type"] != repo_type]

    if archived_status != "All":
        df_dependabot = df_dependabot.loc[
            df_dependabot["Archived Status"] == archived_status
        ]

    return df_dependabot

def add_dependabot_calculations(df_dependabot: pd.DataFrame) -> pd.DataFrame:
    """Add calculated columns to the dependabot DataFrame.

    Args:
        df_dependabot (pd.DataFrame): The DataFrame containing dependabot data.

    Returns:
        pd.DataFrame: A DataFrame with additional calculated columns.
    """
    
    # Map the severity to a numeric value for sorting
    severity_map = {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1,
    }

    df_dependabot["Severity Numeric"] = df_dependabot["Severity"].map(severity_map)
    
    return df_dependabot

def group_dependabot_by_severity(df_dependabot: pd.DataFrame) -> pd.DataFrame:
    """Group dependabot data by severity.

    Args:
        df_dependabot (pd.DataFrame): The DataFrame containing dependabot data.

    Returns:
        pd.DataFrame: A DataFrame grouped by severity with counts.
    """
    
    df_dependabot_grouped_severity = df_dependabot[["Repository", "Severity"]].groupby("Severity").count()
    df_dependabot_grouped_severity.columns = ["Count"]
    
    return df_dependabot_grouped_severity

def group_dependabot_by_repository(df_dependabot: pd.DataFrame) -> pd.DataFrame:
    """Group dependabot data by repository.

    Args:
        df_dependabot (pd.DataFrame): The DataFrame containing dependabot data.

    Returns:
        pd.DataFrame: A DataFrame grouped by repository with aggregated alert counts.
    """
    
    df_dependabot_grouped_repository = df_dependabot[["Repository", "Repository Type", "URL", "Severity"]].groupby(["Repository", "Repository Type", "URL"]).count()
    df_dependabot_grouped_repository.columns = ["Total Alerts"]

    return df_dependabot_grouped_repository
