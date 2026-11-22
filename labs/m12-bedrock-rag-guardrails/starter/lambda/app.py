"""HR assistant Lambda (lab M12): retrieve passages from a Knowledge Base, then
generate an answer with the Converse API under a guardrail.

The JSON keys and the verdict values of the response stay in French because the
lesson's checkpoints read them ("reponse", "sources", "stopReason", "guardrail").
"""

import base64
import json
import os

import boto3

KB_ID = os.environ["KB_ID"]
GUARDRAIL_ID = os.environ["GUARDRAIL_ID"]
GUARDRAIL_VERSION = os.environ["GUARDRAIL_VERSION"]
# Any inference profile or model enabled in the account works through Converse.
MODEL_ID = os.environ.get("MODEL_ID", "eu.anthropic.claude-opus-5-5")
# Anthropic-specific effort setting, passed through to the model's native API.
# Set MODEL_EFFORT to an empty string for a model family that does not accept it.
MODEL_EFFORT = os.environ.get("MODEL_EFFORT", "low")

NUMBER_OF_RESULTS = 4
MAX_QUESTION_LENGTH = 1000
MAX_TOKENS = 2000

kb = boto3.client("bedrock-agent-runtime")
bedrock = boto3.client("bedrock-runtime")

SYSTEM = (
    "Tu es l'assistant RH interne de l'entreprise. Réponds en français, en 120 mots au plus, "
    "uniquement à partir des extraits fournis. Si les extraits ne permettent pas de répondre, "
    "dis-le simplement et oriente vers le service RH."
)

BAD_REQUEST = "question absente ou trop longue (1 000 caractères au plus)"


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _verdict(trace):
    # The trace holds the detected values in clear text: only the verdict is returned.
    serialized = json.dumps(trace)
    if '"BLOCKED"' in serialized:
        return "bloqué"
    if '"ANONYMIZED"' in serialized:
        return "masqué"
    return "intervention"


def _question(event):
    """Return the stripped question from an API Gateway (HTTP API) event, or None."""
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    question = payload.get("question")
    if not isinstance(question, str):
        return None
    question = question.strip()
    if not question or len(question) > MAX_QUESTION_LENGTH:
        return None
    return question


def _model_request_fields():
    if not MODEL_EFFORT:
        return {}
    return {"additionalModelRequestFields": {"output_config": {"effort": MODEL_EFFORT}}}


def handler(event, context):
    question = _question(event)
    if question is None:
        return _response(400, {"erreur": BAD_REQUEST})

    # TODO (step 6): retrieve NUMBER_OF_RESULTS passages with kb.retrieve(knowledgeBaseId=KB_ID, ...).
    # TODO (step 6): join the passages as "[1] text", "[2] text"... and collect the sorted,
    #                unique S3 URIs of their locations as the sources.
    # TODO (step 6): call bedrock.converse(modelId=MODEL_ID, system=[{"text": SYSTEM}], ...) with
    #                one user message made of two guardContent blocks: the excerpts qualified as
    #                "grounding_source" (or "Aucun extrait." when there is none), and the question
    #                qualified as "query" and "guard_content"; inferenceConfig maxTokens MAX_TOKENS;
    #                guardrailConfig with GUARDRAIL_ID, GUARDRAIL_VERSION and trace "enabled";
    #                and **_model_request_fields().
    # TODO (step 6): return 200 with {"reponse", "sources", "stopReason", "guardrail", "usage"},
    #                where "guardrail" is "aucun", or _verdict(trace) when stopReason is
    #                "guardrail_intervened".
    return _response(501, {"erreur": "TODO (step 6): retrieve then generate"})
