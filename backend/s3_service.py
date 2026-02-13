"""
S3 session recording service for Story Engine.
Fire-and-forget uploads — never blocks user, silently skipped if not configured.
"""

import os
import json
import uuid
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Read S3 config from environment
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def is_configured():
    """Check if S3 credentials are configured."""
    return bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_S3_BUCKET)


def _get_s3_client():
    """Create a boto3 S3 client with configured credentials."""
    import boto3
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def _upload_to_s3(key, body):
    """Synchronous S3 upload (runs in executor)."""
    s3 = _get_s3_client()
    s3.put_object(
        Bucket=AWS_S3_BUCKET,
        Key=key,
        Body=body,
        ContentType="application/json",
    )


def list_prefixes(prefix, delimiter="/"):
    """List subdirectory prefixes under a given S3 prefix (synchronous)."""
    s3 = _get_s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    prefixes = []
    for page in paginator.paginate(Bucket=AWS_S3_BUCKET, Prefix=prefix, Delimiter=delimiter):
        for cp in page.get("CommonPrefixes", []):
            prefixes.append(cp["Prefix"])
    return prefixes


def list_files(prefix):
    """List files under a given S3 prefix, newest first (synchronous)."""
    s3 = _get_s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    files = []
    for page in paginator.paginate(Bucket=AWS_S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            files.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            })
    files.sort(key=lambda f: f["last_modified"], reverse=True)
    return files


def get_object(key):
    """Get the body of an S3 object as a string (synchronous)."""
    s3 = _get_s3_client()
    resp = s3.get_object(Bucket=AWS_S3_BUCKET, Key=key)
    return resp["Body"].read().decode("utf-8")


async def record_session(page, action, step_info, model_id, outputs, step_num=None):
    """Record a session event to S3 (fire-and-forget).

    Args:
        page: "story" or "ideas"
        action: "generate", "evaluate", etc.
        step_info: dict with step-specific data (num, title, prompts, etc.)
        model_id: the model used
        outputs: current outputs dict
        step_num: step number (0, 1, 2, etc.) or None for actions without a step
    """
    if not is_configured():
        return

    try:
        now = datetime.utcnow()
        record = {
            "timestamp": now.isoformat() + "Z",
            "page": page,
            "action": action,
            "model_id": model_id,
            "step_info": step_info,
            "outputs": outputs,
        }
        body = json.dumps(record, indent=2)
        date_str = now.strftime("%Y-%m-%d")
        ts_str = now.strftime("%d-%H-%M-%S")
        uid = uuid.uuid4().hex[:8]
        step_part = f"_step{step_num}" if step_num is not None else ""
        key = f"sessions/{page}/{date_str}/{ts_str}_{action}{step_part}_{uid}.json"

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _upload_to_s3, key, body)
    except Exception as e:
        logger.warning(f"S3 record_session failed: {e}")
