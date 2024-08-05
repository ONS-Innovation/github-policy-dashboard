# import api_interface
import github_api_toolkit
import policy_checks

import json
import boto3
import os

org = os.getenv("GITHUB_ORG")
client_id = os.getenv("GITHUB_APP_CLIENT_ID")

# AWS Secret Manager Secret Name for the .pem file
secret_name = os.getenv("AWS_SECRET_NAME")
secret_reigon = os.getenv("AWS_DEFAULT_REGION")

account = os.getenv("AWS_ACCOUNT_NAME")
bucket_name = f"{account}-github-audit-dashboard"

def handler(event, context):

    print("Starting Execution")

    # Create a boto3 session
    session = boto3.Session()

    print("Created Boto3 Session")

    # Get the .pem file from AWS Secrets Manager
    secret_manager = session.client("secretsmanager", region_name=secret_reigon)

    secret = secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]

    print("Got .pem file from AWS Secrets Manager")

    token = github_api_toolkit.get_token_as_installation(org, secret, client_id)

    # Check if the token is a string, if it is then an error occurred
    if type(token) == str:
        print("Failed to get GitHub Access Token")
        return

    print("Got GitHub Access Token")

    gh = github_api_toolkit.github_interface(token[0])

    print("Created GitHub API Controller")

    repos = policy_checks.get_repository_data(gh, org)

    print("Got Repository Data")

    with open("/tmp/repositories.json", "w") as f:
        f.write(json.dumps(repos, indent=4))

    secret_scanning_alerts = policy_checks.get_security_alerts(gh, org, 5, "secret_scanning")

    with open("/tmp/secret_scanning.json", "w") as f:
        f.write(json.dumps(secret_scanning_alerts, indent=4))

    print("Got Secret Scanning Alerts")

    dependabot_alerts = policy_checks.get_all_dependabot_alerts(gh, org)

    with open("/tmp/dependabot.json", "w") as f:
        f.write(json.dumps(dependabot_alerts, indent=4))

    print("Got Dependabot Alerts")

    s3 = session.client('s3')

    print("Created S3 Client")

    s3.upload_file("/tmp/repositories.json", bucket_name, "repositories.json")

    print("Uploaded Repositories JSON to S3")

    s3.upload_file("/tmp/secret_scanning.json", bucket_name, "secret_scanning.json")

    print("Uploaded Secret Scanning JSON to S3")

    s3.upload_file("/tmp/dependabot.json", bucket_name, "dependabot.json")

    print("Uploaded Dependabot JSON to S3")

    print("Finished Execution")
