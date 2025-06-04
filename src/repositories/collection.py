"""A module for managing the collection of repository data for the dashboard."""

import streamlit as st
from botocore.exceptions import ClientError
import pandas as pd
from datetime import timedelta
import json

@st.cache_data(ttl=timedelta(hours=1))
def load_repositories(_s3, bucket: str) -> pd.DataFrame | None:
    """Load repository data from an S3 bucket and return it as a DataFrame.

    Args:
        _s3 (boto3.client): A Boto3 S3 client to interact with AWS S3.
        bucket (str): The name of the S3 bucket containing the repository data.

    Returns:s
        pd.DataFrame | None: A DataFrame containing the repository data or None if the data could not be loaded.
    """

    try:
        response = _s3.get_object(Bucket=bucket, Key="repositories.json")
    except ClientError as e:
        return None
    
    # Convert the JSON data to a Pandas DataFrame
    json_data = json.loads(response["Body"].read().decode("utf-8"))

    df_repositories = pd.json_normalize(json_data)

    # Update repository_type to be title case
    df_repositories["type"] = df_repositories["type"].str.title()

    return df_repositories

@st.cache_data(ttl=timedelta(hours=1))
def load_rulemap() -> dict | None:
    """Load the rule map from a JSON file and return it as a dictionary.

    Returns:
        dict | None: A dictionary containing the rule map or None if the file could not be found.
    """
    
    try:
        with open("./rulemap.json") as file:
            rulemap = json.load(file)
    except FileNotFoundError as e:
        return None
    
    return rulemap
