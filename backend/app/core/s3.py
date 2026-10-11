import boto3
from botocore.exceptions import ClientError
from app.config import settings

from typing import Dict, Any

_boto_kwargs: Dict[str, Any] = {"region_name": settings.AWS_REGION}
if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
    _boto_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
    _boto_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

s3 = boto3.client("s3", **_boto_kwargs)

def upload_image_bytes(s3_key: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Uploads raw image bytes to the CivicPulse S3 bucket."""
    s3.put_object(
        Bucket=settings.S3_BUCKET,
        Key=s3_key,
        Body=data,
        ContentType=content_type,
    )
    return f"s3://{settings.S3_BUCKET}/{s3_key}"

def get_image_bytes(s3_key: str) -> bytes:
    """Retrieves image bytes from S3 for Groq audit inspection."""
    res = s3.get_object(Bucket=settings.S3_BUCKET, Key=s3_key)
    return res["Body"].read()

def generate_presigned_view_url(s3_key: str, expiration_seconds: int = 604800) -> str:
    """Generates a presigned GET URL (7-day validity for civic notices)."""
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": s3_key},
            ExpiresIn=expiration_seconds,
        )
    except ClientError as e:
        print(f"[S3 Error] Presigned URL failed: {e}")
        return ""