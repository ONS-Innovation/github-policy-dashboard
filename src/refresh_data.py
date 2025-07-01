"""A Python script to refresh the dataset for the GitHub Policy Dashboard."""

import botocore.config
import boto3
import botocore
from requests import Response
import datetime

import utilities as utils

def refresh_data() -> dict:
    """A function to refresh the dataset for the GitHub Policy Dashboard.

    Returns:
        dict: A dictionary containing the status of the data refresh operation and a message.
    """

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
        return {"status": "error", "message": "Error fetching rate limit from GitHub API."}
    
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

        return {"status": "error", "message": f"GitHub API rate limit exceeded. Please try again after {reset_time}."}
    
    if remaining["graphql"]["remaining"] < 8000:

        reset_time = datetime.datetime.fromtimestamp(
            remaining["graphql"]["reset"]
        ).strftime("%H:%M")

        return {"status": "error", "message": f"GitHub GraphQL API rate limit exceeded. Please try again after {reset_time}."}
    
    # Proceed with data refresh

    lambda_config = botocore.config.Config(
        read_timeout=900,  # 15 minutes (Maximum timeout for Lambda)
        retries={
            "total_max_attempts": 1,
        }
    )

    lambda_client = session.client("lambda", region_name=env["secret_region"], config=lambda_config)

    response = lambda_client.invoke(
        FunctionName="policy-dashboard-lambda",
        InvocationType="RequestResponse",
    )

    if response["StatusCode"] != 200:
        return {"status": "error", "message": "Error invoking Lambda function to refresh dataset."}
    
    if "FunctionError" in response:
        return {"status": "error", "message": "Error in Lambda function execution."}

    return {"status": "success", "message": "Dataset refreshed successfully!"}
