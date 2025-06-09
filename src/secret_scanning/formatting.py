"""A module to format secret scanning data for the dashboard."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import boto3

from utilities import get_rest_interface, get_github_repository_information

@st.cache_data(ttl=timedelta(hours=1))
def add_repository_information(
    df_secret_scanning: pd.DataFrame,
    _secret_manager: boto3.client,
    secret_name: str,
    org: str,
    client_id: str,
) -> pd.DataFrame:
    """Add additional repository information to the secret scanning DataFrame.

    Args:
        df_secret_scanning (pd.DataFrame): The DataFrame containing secret scanning data.
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
        repository_list=df_secret_scanning["Repository"].unique().tolist(),
    )

    # Add a new column for repository type
    df_secret_scanning["Repository Type"] = df_secret_scanning["Repository"].map(repo_types)

    # Add a new column for archived status
    df_secret_scanning["Archived Status"] = df_secret_scanning["Repository"].map(archived_status)

    return df_secret_scanning

@st.cache_data(ttl=timedelta(hours=1))
def filter_secret_scanning(
    df_secret_scanning: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    types_to_exclude: list,
    archived_status: str,
) -> pd.DataFrame:
    """Filter secret scanning data based on user inputs.

    Args:
        df_secret_scanning (pd.DataFrame): The DataFrame containing secret scanning data.
        start_date (pd.Timestamp): The start date for filtering.
        end_date (pd.Timestamp): The end date for filtering.
        types_to_exclude (list): The types of repository to filter by.
        archived_status (str): The archived status to filter by. Options are "All", "Archived", or "Not Archived".

    Returns:
        pd.DataFrame: A filtered DataFrame based on the provided criteria.
    """
    
    df_secret_scanning = df_secret_scanning.loc[
        (df_secret_scanning["Creation Date"] >= pd.to_datetime(start_date))
        & (df_secret_scanning["Creation Date"] <= pd.to_datetime(end_date))
    ]

    for type_to_exclude in types_to_exclude:
        df_secret_scanning = df_secret_scanning.loc[
            df_secret_scanning["Repository Type"] != type_to_exclude
        ]

    if archived_status != "All":
        df_secret_scanning = df_secret_scanning.loc[
            df_secret_scanning["Archived Status"] == archived_status
        ]

    return df_secret_scanning

def group_secret_scanning_by_repository(df_secret_scanning: pd.DataFrame) -> pd.DataFrame:
    """Group secret scanning data by repository.

    Args:
        df_secret_scanning (pd.DataFrame): The DataFrame containing secret scanning data.

    Returns:
        pd.DataFrame: A DataFrame grouped by repository with aggregated alert counts.
    """
    
    df_grouped_secrets = df_secret_scanning[["Repository", "Creation Date"]].groupby("Repository").count()
    df_grouped_secrets.columns = ["Total Alerts"]

    return df_grouped_secrets
    