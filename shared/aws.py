import os
import boto3
from boto3.session import Session


def set_s3_client(aws_region: str):
    # Use SSO profile when running locally, not lambda
    if os.getenv("AWS_EXECUTION_ENV") is None:
        print("🔹 Running locally with SSO profile")
        session = Session(profile_name="ronantfs")
        s3 = session.client("s3", region_name=aws_region)
    else:
        print("🔹 Running inside AWS Lambda environment")
        s3 = boto3.client("s3", region_name=aws_region)
    return s3


def _generate_presigned_url(
    s3_client, bucket: str, key: str, expires_in: int = 300
) -> str:
    """
    Generate a temporary presigned URL for an S3 object.

    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
        expires_in (int): expiration time in seconds (default 5 min)

    Returns:
        str: presigned S3 URL
    """
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,  # short-lived URL
        )
    except Exception as e:
        print(f"Failed to generate presigned URL for {key}: {e}")
        return None
