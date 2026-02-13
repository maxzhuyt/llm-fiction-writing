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


def _upload_to_s3(key, body):
    """Synchronous S3 upload (runs in executor)."""
    import boto3
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    s3.put_object(
        Bucket=AWS_S3_BUCKET,
        Key=key,
        Body=body,
        ContentType="application/json",
    )


async def record_session(page, action, step_info, model_id, outputs):
    """Record a session event to S3 (fire-and-forget).

    Args:
        page: "story" or "ideas"
        action: "generate", "evaluate", etc.
        step_info: dict with step-specific data (num, title, prompts, etc.)
        model_id: the model used
        outputs: current outputs dict
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
        ts_str = now.strftime("%H%M%S")
        uid = uuid.uuid4().hex[:8]
        key = f"sessions/{page}/{date_str}/{ts_str}_{uid}.json"

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _upload_to_s3, key, body)
    except Exception as e:
        logger.warning(f"S3 record_session failed: {e}")
