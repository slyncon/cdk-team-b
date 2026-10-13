"""Read-only processing of synthetic metadata; never use real health data."""

import json
import logging
import os
from urllib.parse import unquote_plus

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict, context: object) -> dict:
    s3 = boto3.client("s3")
    processed = 0
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        response = s3.get_object(Bucket=bucket, Key=key)
        with response["Body"] as body:
            try:
                document = json.load(body)
            except (ValueError, UnicodeDecodeError) as error:
                raise ValueError("Medical metadata must contain valid JSON") from error
        if not isinstance(document, dict):
            raise ValueError("Medical metadata must be a JSON object")
        for field in ("document_id", "type", "status"):
            if not isinstance(document.get(field), str) or not document[field].strip():
                raise ValueError(f"Medical metadata requires a nonempty string: {field}")
        logger.info(
            json.dumps(
                {
                    "team": os.getenv("TEAM", "medical-documents"),
                    "document_id": document["document_id"],
                    "result": "processed",
                }
            )
        )
        processed += 1
    return {"processed": processed}
