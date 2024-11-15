"""
    This script is run to populate the initial data for the policy lambda. AWS Lambda has a maximum timeout value of 15 minutes.
    This script takes the lambda logic from main.py and runs it outside of lambda configurations so it isn't capped to 15 minutes.
    It also tests for potential rate limits through the API and any long-term running issues.
"""

import github_api_toolkit
import policy_checks

import json
import boto3
import os
import datetime

org = os.getenv("GITHUB_ORG")
client_id = os.getenv("GITHUB_APP_CLIENT_ID")

# AWS Secret Manager Secret Name for the .pem file
secret_name = os.getenv("AWS_SECRET_NAME")
secret_reigon = os.getenv("AWS_DEFAULT_REGION")

account = os.getenv("AWS_ACCOUNT_NAME")
bucket_name = f"{account}-github-audit-dashboard"

start = datetime.datetime.now()

print("start" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Create a boto3 session
session = boto3.Session()

print("Created Boto3 Session")

# Get the .pem file from AWS Secrets Manager
secret_manager = session.client("secretsmanager", region_name=secret_reigon)

print("Secrets Manager Client Created")

secret = secret_manager.get_secret_value(SecretId=secret_name)["SecretString"]

token = github_api_toolkit.get_token_as_installation(org, secret, client_id)

# Check if the token is a string, if it is then an error occurred
if type(token) == str:
    print(f"Error getting token: {token}")

else:
    print("Got GitHub Access Token using AWS Secret")

gh = github_api_toolkit.github_interface(token[0])
ql = github_api_toolkit.github_graphql_interface(token[0])

print("Created API Controller")

s3 = session.client("s3")

print("S3 Client Created")

try:
    existing_repos = s3.get_object(Bucket=bucket_name, Key="test_repositories.json")
    existing_repos = json.loads(existing_repos["Body"].read().decode("utf-8"))
except s3.exceptions.NoSuchKey:
    existing_repos = []

try:
    last_run_date = s3.get_object(Bucket=bucket_name, Key="test_last_updated.txt")
    last_run_date = datetime.datetime.strptime(last_run_date["Body"].read().decode("utf-8"), "%Y-%m-%d %H:%M:%S")
except s3.exceptions.NoSuchKey:
    last_run_date = datetime.datetime(1900, 1, 1)

updated_repos = policy_checks.get_repository_data(gh, ql, org, existing_repos, last_run_date)

repos = updated_repos["repo_list"]

print(f"Repository Data Retrieved \n total_records: {len(repos)}, \n updated_records: {updated_repos["repos_updated"]}")

secret_scanning_alerts = policy_checks.get_security_alerts(gh, org, 5, "secret_scanning")

print(f"Secret Scanning Alerts Retrieved: {len(secret_scanning_alerts)}")

dependabot_alerts = policy_checks.get_all_dependabot_alerts(gh, org)

print(f"Dependabot Alerts Retrieved {len(dependabot_alerts)}")

s3.put_object(
    Bucket=bucket_name,
    Key="test_repositories.json",
    Body=json.dumps(repos, indent=4).encode("utf-8"),
)

print("Uploaded Repositories JSON to S3")

s3.put_object(
    Bucket=bucket_name,
    Key="test_secret_scanning.json",
    Body=json.dumps(secret_scanning_alerts, indent=4).encode("utf-8"),
)

print("Uploaded Secret Scanning JSON to S3")

s3.put_object(
    Bucket=bucket_name,
    Key="test_dependabot.json",
    Body=json.dumps(dependabot_alerts, indent=4).encode("utf-8"),
)

print("Uploaded Dependabot JSON to S3")

s3.put_object(
    Bucket=bucket_name,
    Key="test_last_updated.txt",
    Body=datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S"),
)

print(f"Process Complete \n bucket: {bucket_name}, \n no_repos: {len(repos)}, \n no_secret_alerts: {len(secret_scanning_alerts)}, \n no_dependabot_alerts: {len(dependabot_alerts)}")

print("end" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

runtime = datetime.datetime.now() - start

print("Runtime: " + runtime.seconds + " seconds")