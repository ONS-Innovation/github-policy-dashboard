"""A module for managing the collection of secret scanning data for the dashboard."""

import streamlit as st
from botocore.exceptions import ClientError
import pandas as pd
from datetime import datetime, timedelta
import json

@st.cache_data(ttl=timedelta(hours=1))
def load_secret_scanning(_s3, bucket: str) -> pd.DataFrame | None:
    """Load secret scanning data from an S3 bucket and return it as a DataFrame.

    Args:
        _s3 (boto3.client): A Boto3 S3 client to interact with AWS S3.
        bucket (str): The name of the S3 bucket containing the secret scanning data.

    Returns:
        pd.DataFrame | None: A DataFrame containing the secret scanning data or None if the data could not be loaded.
    """

    # Get secret_scanning.json from S3
    try:
        response = _s3.get_object(Bucket=bucket, Key="secret_scanning.json")
    except ClientError as e:
        return None
    
    # Convert the response to a JSON object
    json_data = json.loads(response["Body"].read().decode("utf-8"))

    df_secret_scanning = pd.json_normalize(json_data)

    # Rename the columns to be more readable
    df_secret_scanning.columns = [
        "Repository",
        "Creation Date",
        "URL",
    ]

    # Add Alert Age (Days) to the DataFrame
    df_secret_scanning["Alert Age (Days)"] = datetime.now() - pd.to_datetime(df_secret_scanning["Creation Date"]).dt.tz_localize(None)
    df_secret_scanning["Alert Age (Days)"] = df_secret_scanning["Alert Age (Days)"].dt.days
    df_secret_scanning["Alert Age (Days)"] = df_secret_scanning["Alert Age (Days)"].astype(int)

    # Remove the timezone information from the Creation Date
    df_secret_scanning["Creation Date"] = pd.to_datetime(df_secret_scanning["Creation Date"], errors="coerce").dt.tz_localize(None)


    return df_secret_scanning
