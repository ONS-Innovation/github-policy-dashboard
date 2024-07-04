from src.app import get_table_from_s3

import boto3
import pandas as pd

def get_s3_client() -> boto3.client:
    session = boto3.Session(profile_name="ons_sdp_sandbox")
    s3 = session.client("s3")
    return s3

def test_invalid_bucket() -> None:
    """
    Test that the function returns a string when an invalid bucket is provided
    """
    s3 = get_s3_client()

    bucket = "invalid-bucket"
    object_name = "repositories.json"
    filename = "repositories.json"

    assert type(get_table_from_s3(s3, bucket, object_name, filename)) == str

def test_invalid_object_name() -> None:
    """
    Test that the function returns a string when an invalid object name is provided
    """
    s3 = get_s3_client()

    bucket = "sdp-sandbox-github-audit-dashboard"
    object_name = "invalid-object-name"
    filename = "repositories.json"

    assert type(get_table_from_s3(s3, bucket, object_name, filename)) == str

def test_correct_input() -> None:
    """
    Test that the function returns a DataFrame when correct input is provided
    """
    s3 = get_s3_client()

    bucket = "sdp-sandbox-github-audit-dashboard"
    object_name = "repositories.json"
    filename = "repositories.json"

    assert type(get_table_from_s3(s3, bucket, object_name, filename)) == pd.DataFrame