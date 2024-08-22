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

def handler(event, context):

    logger.info("Starting Process")

    logger.info("Creating Boto3 Session")

    # Create a boto3 session
    session = boto3.Session()

    logger.info("Created Boto3 Session")

    logger.info("Creating Secrets Manager Client")

    # Get the .pem file from AWS Secrets Manager
    secret_manager = session.client("secretsmanager", region_name=secret_reigon)

    logger.info("Secrets Manager Client Created")

    logger.info("Getting secret from Secrets Manager")

    secret = secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]

    logger.info("Got Secret from Secrets Manager")

    logger.info("Getting access token")

    token = github_api_toolkit.get_token_as_installation(org, secret, client_id)

    # Check if the token is a string, if it is then an error occurred
    if type(token) == str:
        logger.error(f"Error getting token: {token}")
        return f"Error getting token: {token}"

    else:
        logger.info("Got GitHub Access Token")

    logger.info("Creating API Controller")

    gh = github_api_toolkit.github_interface(token[0])

    logger.info("Created API Controller")

    logger.info("Getting Repository Data")

    repos = policy_checks.get_repository_data(gh, org)

    logger.info("Repository Data Retrieved")

    logger.info("Getting Secret Scanning Alerts")

    secret_scanning_alerts = policy_checks.get_security_alerts(gh, org, 5, "secret_scanning")

    logger.info("Secret Scanning Alerts Retrieved")

    logger.info("Getting Dependabot Alerts")

    dependabot_alerts = policy_checks.get_all_dependabot_alerts(gh, org)

    logger.info("Dependabot Alerts Retrieved")

    logger.info("Pushing Data to S3")

    logger.info("Creating S3 Client")

    s3 = session.client('s3')

    logger.info("Created S3 Client")

    s3.put_object(Bucket=bucket_name, Key="repositories.json", Body=json.dumps(repos, indent=4).encode("utf-8"))

    logger.info("Uploaded Repositories JSON to S3")

    s3.put_object(Bucket=bucket_name, Key="secret_scanning.json", Body=json.dumps(secret_scanning_alerts, indent=4).encode("utf-8"))

    logger.info("Uploaded Secret Scanning JSON to S3")

    s3.put_object(Bucket=bucket_name, Key="dependabot.json", Body=json.dumps(dependabot_alerts, indent=4).encode("utf-8"))

    logger.info("Uploaded Dependabot JSON to S3")

    logger.info("Process Complete")