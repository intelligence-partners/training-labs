"""Prompt registry: POST /prompts and GET /prompts/{id} behind an API Gateway HTTP API.

The JSON field names (nom, texte, creeLe, erreur), the error messages and the
prompt_cree log event stay in French: the course checkpoints rely on them.
nom = name, texte = text, creeLe = created at, erreur = error.
"""

import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

MAX_NAME = 100
MAX_TEXT = 10_000


def response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def read_body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    return json.loads(raw)


def create_prompt(event):
    try:
        data = read_body(event)
    except (ValueError, UnicodeDecodeError):
        return response(400, {"erreur": "corps JSON invalide"})
    if not isinstance(data, dict):
        return response(400, {"erreur": "un objet JSON est attendu"})
    name = str(data.get("nom", "")).strip()
    text = str(data.get("texte", "")).strip()
    if not name or len(name) > MAX_NAME:
        return response(400, {"erreur": "nom obligatoire, 100 caractères au plus"})
    if not text or len(text) > MAX_TEXT:
        return response(400, {"erreur": "texte obligatoire, 10 000 caractères au plus"})
    item = {
        "id": uuid.uuid4().hex,
        "nom": name,
        "texte": text,
        "creeLe": datetime.now(timezone.utc).isoformat(),
    }
    table.put_item(Item=item)
    # Log the ID and the size only, never the prompt text.
    logger.info("prompt_cree id=%s taille=%d", item["id"], len(text))
    return response(201, item)


def get_prompt(event):
    prompt_id = (event.get("pathParameters") or {}).get("id", "")
    item = table.get_item(Key={"id": prompt_id}).get("Item")
    if not item:
        return response(404, {"erreur": "prompt introuvable"})
    return response(200, item)


def handler(event, context):
    # HTTP APIs (payload format 2.0) pass the matched route in routeKey.
    route = event.get("routeKey")
    if route == "POST /prompts":
        return create_prompt(event)
    if route == "GET /prompts/{id}":
        return get_prompt(event)
    return response(404, {"erreur": "route inconnue"})
