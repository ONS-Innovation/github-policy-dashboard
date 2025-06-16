"""A module for managing the collection of dependabot data for the dashboard."""

import streamlit as st
from botocore.exceptions import ClientError
import pandas as pd
from datetime import datetime, timedelta
import json

@st.cache_data(ttl=timedelta(hours=1))
def load_dependabot(_s3, bucket: str) -> pd.DataFrame | None:
    """Load Dependabot data from an S3 bucket and return it as a DataFrame.

    Args:
        _s3 (boto3.client): A Boto3 S3 client to interact with AWS S3.
        bucket (str): The name of the S3 bucket where the Dependabot data is stored.

    Returns:
        pd.DataFrame | None: A DataFrame containing the Dependabot data, or None if an error occurs.
    """

    # Get dependabot.json from S3
    try:
        response = _s3.get_object(Bucket=bucket, Key="dependabot.json")
    except ClientError as e:
        return None
    
    # Convert the response to a JSON object
    json_data = json.loads(response["Body"].read().decode("utf-8"))

    df_dependabot = pd.json_normalize(json_data)

    if df_dependabot.empty:
        return None

    # Rename the columns to be more readable
    df_dependabot.columns = [
        "Repository",
        "URL",
        "Creation Date",
        "Severity",
        "Alert URL",
    ]

    # Remove alert URL since it isn't used (Database requirement only)
    df_dependabot = df_dependabot.drop(columns=["Alert URL"])

    # Add Alert Age (Days) to the DataFrame
    df_dependabot["Alert Age (Days)"] = datetime.now() - pd.to_datetime(df_dependabot["Creation Date"]).dt.tz_localize(None)
    df_dependabot["Alert Age (Days)"] = df_dependabot["Alert Age (Days)"].dt.days
    df_dependabot["Alert Age (Days)"] = df_dependabot["Alert Age (Days)"].astype(int)

    # Title Case the Severity column
    df_dependabot["Severity"] = df_dependabot["Severity"].str.title()

    # Remove the timezone information from the Creation Date
    df_dependabot["Creation Date"] = pd.to_datetime(df_dependabot["Creation Date"], errors="coerce").dt.tz_localize(None)

    return df_dependabot
