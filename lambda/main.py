import api_interface
import policy_checks

import json
import boto3

org = "ONS-Innovation"
client_id = "Iv23lifHcR6yRDTxa7nk"

# AWS Secret Manager Secret Name for the .pem file
secret_name = "/sdp/tools/repoarchive/repo-archive-github.pem"
secret_reigon = "eu-west-2"

def handler(event, context):

    print("Starting Execution")

    # Create a boto3 session
    session = boto3.Session()

    print("Created Boto3 Session")

    # Get the .pem file from AWS Secrets Manager
    secret_manager = session.client("secretsmanager", region_name=secret_reigon)

    secret = secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]

    print("Got .pem file from AWS Secrets Manager")

    token = api_interface.get_access_token(org, secret, client_id)

    print("Got GitHub Access Token")

    gh = api_interface.api_controller(token[0])

    print("Created GitHub API Controller")

    repos = policy_checks.get_repository_data(gh, org)

    print("Got Repository Data")

    with open("/tmp/repositories.json", "w") as f:
        f.write(json.dumps(repos, indent=4))

    secret_scanning_alerts = policy_checks.get_secret_scanning_alerts(gh, org, 5)

    with open("/tmp/secret_scanning.json", "w") as f:
        f.write(json.dumps(secret_scanning_alerts, indent=4))

    print("Got Secret Scanning Alerts")

    dependabot_alerts = policy_checks.get_all_dependabot_alerts(gh, org)

    with open("/tmp/dependabot.json", "w") as f:
        f.write(json.dumps(dependabot_alerts, indent=4))

    print("Got Dependabot Alerts")

    s3 = session.client('s3')

    print("Created S3 Client")

    s3.upload_file("/tmp/repositories.json", "sdp-sandbox-github-audit-dashboard", "repositories.json")

    print("Uploaded Repositories JSON to S3")

    s3.upload_file("/tmp/secret_scanning.json", "sdp-sandbox-github-audit-dashboard", "secret_scanning.json")

    print("Uploaded Secret Scanning JSON to S3")

    s3.upload_file("/tmp/dependabot.json", "sdp-sandbox-github-audit-dashboard", "dependabot.json")

    print("Uploaded Dependabot JSON to S3")

    print("Finished Execution")