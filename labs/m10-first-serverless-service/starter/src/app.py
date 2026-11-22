"""Prompt registry: POST /prompts and GET /prompts/{id} behind an API Gateway HTTP API.

Starter file for step 2 of the lab. Complete every TODO, then run the tests
against your work (see the README): LAB_TARGET=starter bash test.sh

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
    # TODO (step 2): read the body with read_body(); answer 400
    #   {"erreur": "corps JSON invalide"} if it is not valid JSON, and
    #   {"erreur": "un objet JSON est attendu"} if it is not an object.
    # TODO (step 2): validate "nom" (1 to MAX_NAME characters, else 400
    #   {"erreur": "nom obligatoire, 100 caractères au plus"}) and "texte"
    #   (1 to MAX_TEXT characters, else 400
    #   {"erreur": "texte obligatoire, 10 000 caractères au plus"}).
    # TODO (step 2): build the item {"id": uuid4 hex, "nom", "texte",
    #   "creeLe": UTC ISO 8601 date}, write it with table.put_item(), log
    #   "prompt_cree id=%s taille=%d" (never the text) and answer 201 with it.
    return response(501, {"erreur": "TODO"})


def get_prompt(event):
    # TODO (step 2): read pathParameters["id"], fetch the item with
    #   table.get_item(); answer 200 with it, or 404 {"erreur": "prompt introuvable"}.
    return response(501, {"erreur": "TODO"})


def handler(event, context):
    # HTTP APIs (payload format 2.0) pass the matched route in routeKey.
    route = event.get("routeKey")
    if route == "POST /prompts":
        return create_prompt(event)
    if route == "GET /prompts/{id}":
        return get_prompt(event)
    return response(404, {"erreur": "route inconnue"})
