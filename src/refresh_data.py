"""A Python script to refresh the dataset for the GitHub Policy Dashboard."""

import streamlit as st
import boto3
from requests import Response
import datetime

import utilities as utils

def refresh_data():
    """Refresh the dataset from GitHub."""

    # Check GitHub API rate limit
    # If not enough rate limit, show error message and say when to try again
    # If enough rate limit, proceed with data refresh

    env = utils.get_environment_variables()

    session = boto3.Session()
    secret_manager = session.client("secretsmanager", region_name=env["secret_region"])

    rest = utils.get_rest_interface(
        secret_manager,
        env["secret_name"],
        env["org"],
        env["client_id"]
    )

    response = rest.get("/rate_limit")

    if type(response) is not Response:
        st.error("Error fetching rate limit from GitHub API.")
        return
    
    rate_limit = response.json()

    remaining = {
        "rest": {
            "remaining": rate_limit["rate"]["remaining"],
            "reset": rate_limit["rate"]["reset"]
        },
        "graphql": {
            "remaining": rate_limit["resources"]["graphql"]["remaining"],
            "reset": rate_limit["resources"]["graphql"]["reset"]
        }
    }

    if remaining["rest"]["remaining"] < 5000:

        reset_time = datetime.datetime.fromtimestamp(
            remaining["rest"]["reset"]
        ).strftime("%H:%M")

        st.error(
            f"GitHub API rate limit exceeded. Please try again after {reset_time}."
        )
        return
    
    if remaining["graphql"]["remaining"] < 8000:

        reset_time = datetime.datetime.fromtimestamp(
            remaining["graphql"]["reset"]
        ).strftime("%H:%M")

        st.error(
            f"GitHub GraphQL API rate limit exceeded. Please try again after {reset_time}."
        )
        return
    
    # Proceed with data refresh

    lambda_client = session.client("lambda", region_name=env["secret_region"])

    response = lambda_client.invoke(
        FunctionName="policy-dashboard-lambda",
        InvocationType="RequestResponse",
    )

    if response["StatusCode"] != 200:
        st.error("Error invoking Lambda function to refresh dataset.")
        return
    
    if "FunctionError" in response:
        st.error("Error in Lambda function execution. Please check the logs.")
        return
    
    st.success("Dataset refreshed successfully!")

    # Clear cache to ensure fresh data is loaded
    st.cache_data.clear()

    return
