# import api_interface
import github_api_toolkit
import policy_checks

import json
import boto3
import os
import logging

org = os.getenv("GITHUB_ORG")
client_id = os.getenv("GITHUB_APP_CLIENT_ID")

# AWS Secret Manager Secret Name for the .pem file
secret_name = os.getenv("AWS_SECRET_NAME")
secret_reigon = os.getenv("AWS_DEFAULT_REGION")

account = os.getenv("AWS_ACCOUNT_NAME")
bucket_name = f"{account}-github-audit-dashboard"

logger = logging.getLogger()

# Example Log Output:
#
# Standard output:
# {
#     "timestamp":"2023-10-27T19:17:45.586Z",
#     "level":"INFO",
#     "message":"Inside the handler function",
#     "logger": "root",
#     "requestId":"79b4f56e-95b1-4643-9700-2807f4e68189"
# }
#
# Output with extra fields:
# {
#     "timestamp":"2023-10-27T19:17:45.586Z",
#     "level":"INFO",
#     "message":"Inside the handler function",
#     "logger": "root",
#     "requestId":"79b4f56e-95b1-4643-9700-2807f4e68189",
#     "records_added": 10
# }

def handler(event, context):

    # Create a boto3 session
    session = boto3.Session()

    logger.info("Created Boto3 Session")

    # Get the .pem file from AWS Secrets Manager
    secret_manager = session.client("secretsmanager", region_name=secret_reigon)

    logger.info("Secrets Manager Client Created")

    secret = secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]

    token = github_api_toolkit.get_token_as_installation(org, secret, client_id)

    # Check if the token is a string, if it is then an error occurred
    if type(token) == str:
        logger.error(f"Error getting token: {token}")
        return f"Error getting token: {token}"

    else:
        logger.info(
            "Got GitHub Access Token using AWS Secret",
            extra = {
                "secret_address": secret_name
            }
        )

    gh = github_api_toolkit.github_interface(token[0])
    ql = github_api_toolkit.github_graphql_interface(token[0])

    logger.info("Created API Controller")

    repos = policy_checks.get_repository_data(gh, ql, org)

    logger.info(
        "Repository Data Retrieved",
        extra= {
            "records_added": len(repos)
        }
    )

    secret_scanning_alerts = policy_checks.get_security_alerts(gh, org, 5, "secret_scanning")

    logger.info(
        "Secret Scanning Alerts Retrieved",
        extra= {
            "records_added": len(secret_scanning_alerts)
        }
    )

    dependabot_alerts = policy_checks.get_all_dependabot_alerts(gh, org)

    logger.info(
        "Dependabot Alerts Retrieved",
        extra= {
            "records_added": len(dependabot_alerts)
        }
    )

    s3 = session.client('s3')

    logger.info("S3 Client Created")

    s3.put_object(Bucket=bucket_name, Key="repositories.json", Body=json.dumps(repos, indent=4).encode("utf-8"))

    logger.info("Uploaded Repositories JSON to S3")

    s3.put_object(Bucket=bucket_name, Key="secret_scanning.json", Body=json.dumps(secret_scanning_alerts, indent=4).encode("utf-8"))

    logger.info("Uploaded Secret Scanning JSON to S3")

    s3.put_object(Bucket=bucket_name, Key="dependabot.json", Body=json.dumps(dependabot_alerts, indent=4).encode("utf-8"))

    logger.info("Uploaded Dependabot JSON to S3")

    logger.info(
        "Process Complete",
        extra = {
            "bucket": bucket_name,
            "no_repos": len(repos),
            "no_secret_alerts": len(secret_scanning_alerts),
            "no_dependabot_alerts": len(dependabot_alerts)
        }
    )