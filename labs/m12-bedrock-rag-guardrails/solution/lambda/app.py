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

    passages = kb.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": question},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": NUMBER_OF_RESULTS}},
    )["retrievalResults"]
    excerpts = "\n\n".join(f"[{i + 1}] {p['content'].get('text', '')}" for i, p in enumerate(passages))
    sources = sorted({p["location"]["s3Location"]["uri"] for p in passages if "s3Location" in p.get("location", {})})

    result = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM}],
        messages=[
            {
                "role": "user",
                "content": [
                    # The excerpts are the grounding source of the contextual grounding check.
                    {"guardContent": {"text": {"text": excerpts or "Aucun extrait.", "qualifiers": ["grounding_source"]}}},
                    # The question is the query, and is also evaluated by the other policies.
                    {"guardContent": {"text": {"text": question, "qualifiers": ["query", "guard_content"]}}},
                ],
            }
        ],
        inferenceConfig={"maxTokens": MAX_TOKENS},
        guardrailConfig={"guardrailIdentifier": GUARDRAIL_ID, "guardrailVersion": GUARDRAIL_VERSION, "trace": "enabled"},
        **_model_request_fields(),
    )

    text = "".join(block.get("text", "") for block in result["output"]["message"]["content"])
    verdict = "aucun"
    if result["stopReason"] == "guardrail_intervened":
        verdict = _verdict(result.get("trace", {}).get("guardrail", {}))
    return _response(
        200,
        {
            "reponse": text,
            "sources": sources,
            "stopReason": result["stopReason"],
            "guardrail": verdict,
            "usage": result["usage"],
        },
    )
