"""A module to format repository data for the dashboard."""

import streamlit as st
import pandas as pd
from datetime import timedelta
from typing import Tuple

@st.cache_data(ttl=timedelta(hours=1))
def get_rules_from_repositories(df_repositories: pd.DataFrame) -> Tuple[list | None, pd.DataFrame]:
    """
    Extracts rules from the repositories DataFrame. Also updates the rules to remove the "checklist." prefix.

    Args:
        df_repositories (pd.DataFrame): DataFrame containing repository data.

    Returns:
        Tuple[list | None, pd.DataFrame]: A tuple containing a list of rules and the updated DataFrame.
        
        If the DataFrame is empty, returns an empty list.
    """
    
    if df_repositories.empty:
        return []

    rules = df_repositories.columns.to_list()[4:]

    # Cleans the rules to remove the "checklist." prefix
    for i in range(len(rules)):
        rules[i] = rules[i].replace("checklist.", "")

    # Rename the dataframe columns to match the rules
    df_repositories.columns = ["repository", "repository_type", "url", "created_at"] + rules
    
    return rules, df_repositories

@st.cache_data(ttl=timedelta(hours=1))
def filter_repositories(
    df_repositories: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    repository_type: str,
    rules_to_exclude: list
) -> pd.DataFrame:
    """
    Filters the repositories DataFrame based on the provided criteria.

    Args:
        df_repositories (pd.DataFrame): DataFrame containing repository data.
        start_date (pd.Timestamp): Start date for filtering.
        end_date (pd.Timestamp): End date for filtering.
        repository_type (str): Type of repository to filter by.
        rule_to_exclude (list): List of rules to exclude from the DataFrame.
    
    Returns:
        pd.DataFrame: Filtered DataFrame containing repository data.
    """

    # Remove the columns for rules that aren't selected
    df_repositories = df_repositories.drop(columns=rules_to_exclude)

    # Filter the DataFrame by the selected repository type
    if repository_type != "All":
        df_repositories = df_repositories.loc[df_repositories["repository_type"] == repository_type]

    # Filter the DataFrame by the selected date range
    df_repositories["created_at"] = pd.to_datetime(df_repositories["created_at"], errors="coerce").dt.tz_localize(
        None
    )
    
    df_repositories = df_repositories.loc[
        (df_repositories["created_at"] >= pd.to_datetime(start_date))
        & (df_repositories["created_at"] <= pd.to_datetime(end_date))
    ]

    return df_repositories

@st.cache_data(ttl=timedelta(hours=1))
def add_repository_calculations(
    df_repositories: pd.DataFrame,
    selected_rules: list
) -> pd.DataFrame:
    """
    Adds calculated columns to the repositories DataFrame based on selected rules.

    Args:
        df_repositories (pd.DataFrame): DataFrame containing repository data.
        selected_rules (list): List of selected rules to calculate.

    Returns:
        pd.DataFrame: Updated DataFrame with calculated columns.
    """
    
    # Create a new column to check if the repository is compliant or not
    # If any check is True, the repository is non-compliant
    df_repositories["is_compliant"] = df_repositories.any(axis="columns", bool_only=True)
    df_repositories["is_compliant"] = df_repositories["is_compliant"].apply(lambda x: not x)

    # Create a new column to count the number of rules broken
    df_repositories["rules_broken"] = df_repositories[selected_rules].sum(axis="columns")

    # Sort the DataFrame by the number of rules broken and the repository name
    df_repositories = df_repositories.sort_values(by=["rules_broken", "repository"], ascending=[False, True])

    # Rename the columns of the DataFrame
    df_repositories.columns = (
        ["Repository", "Repository Type", "URL", "Created At"] + selected_rules + ["Is Compliant", "Rules Broken"]
    )

    return df_repositories

@st.cache_data(ttl=timedelta(hours=1))
def get_compliance_summary(
    df_repositories: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generates a compliance summary DataFrame from the repositories DataFrame.

    Args:
        df_repositories (pd.DataFrame): DataFrame containing repository data.

    Returns:
        pd.DataFrame: Summary DataFrame with compliance statistics.
    """
    
    df_compliance = df_repositories["Is Compliant"].value_counts().reset_index()

    df_compliance["Is Compliant"] = df_compliance["Is Compliant"].apply(
        lambda x: "Compliant" if x else "Non-Compliant"
    )

    df_compliance.columns = ["Compliance", "Number of Repositories"]

    return df_compliance
