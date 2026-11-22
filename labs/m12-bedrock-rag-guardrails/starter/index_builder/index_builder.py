"""Create the k-NN vector index of the Knowledge Base in an OpenSearch Serverless collection.

Terraform invokes this function once (aws_lambda_invocation) with:
    {"endpoint": "https://<id>.<region>.aoss.amazonaws.com", "index": "<name>", "body": {...}}

The call is signed with SigV4 for the "aoss" service using the function's role, which the
collection's data access policy authorizes. Only the standard library and botocore (shipped
with the Lambda Python runtime) are used.
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request

import botocore.session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

SERVICE = "aoss"
# 403 and 404 are expected for a minute or so while the data access policy propagates.
RETRYABLE_STATUSES = {403, 404, 429, 500, 502, 503, 504}
DEFAULT_TIMEOUT_SECONDS = 240
DEFAULT_SETTLE_SECONDS = 20


def _send(method, url, body, region, credentials):
    """Send a SigV4-signed request and return (status, text). Never raises on HTTP errors."""
    data = json.dumps(body).encode("utf-8") if body is not None else b""
    headers = {
        "Content-Type": "application/json",
        # OpenSearch Serverless requires the payload hash header on signed requests.
        "x-amz-content-sha256": hashlib.sha256(data).hexdigest(),
    }
    signed = AWSRequest(method=method, url=url, data=data, headers=headers)
    SigV4Auth(credentials, SERVICE, region).add_auth(signed)
    request = urllib.request.Request(url, data=data or None, method=method, headers=dict(signed.headers.items()))
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")


def _credentials():
    return botocore.session.get_session().get_credentials().get_frozen_credentials()


def create_index(endpoint, index, body, region, credentials, timeout_seconds, settle_seconds):
    url = f"{endpoint.rstrip('/')}/{index}"
    deadline = time.monotonic() + timeout_seconds
    attempt = 0
    while True:
        status, text = _send("PUT", url, body, region, credentials)
        if status in (200, 201):
            result = "created"
            break
        if status == 400 and "resource_already_exists_exception" in text:
            result = "exists"
            break
        if status in RETRYABLE_STATUSES and time.monotonic() < deadline:
            time.sleep(min(2**attempt, 15))
            attempt += 1
            continue
        raise RuntimeError(f"PUT /{index} failed with HTTP {status}: {text[:500]}")

    # Wait until the index is visible, then give the service a moment before the
    # Knowledge Base validates it.
    while True:
        status, _ = _send("HEAD", url, None, region, credentials)
        if status == 200:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError(f"index {index} is still not visible (last HTTP status {status})")
        time.sleep(5)
    time.sleep(settle_seconds)
    return result


def handler(event, context):
    for key in ("endpoint", "index", "body"):
        if key not in event:
            raise ValueError(f"missing '{key}' in the invocation input")
    region = os.environ.get("AWS_REGION") or os.environ["AWS_DEFAULT_REGION"]
    result = create_index(
        endpoint=event["endpoint"],
        index=event["index"],
        body=event["body"],
        region=region,
        credentials=_credentials(),
        timeout_seconds=float(event.get("timeoutSeconds", DEFAULT_TIMEOUT_SECONDS)),
        settle_seconds=float(event.get("settleSeconds", DEFAULT_SETTLE_SECONDS)),
    )
    return {"index": event["index"], "result": result}
