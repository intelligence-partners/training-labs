"""Optional provider switch (not in the lesson): the same summary through Amazon Bedrock.

Enabled with MODEL_PROVIDER=bedrock. The call goes through the Bedrock Runtime Converse
API, which works with every Bedrock model that supports documents and structured output.

What changes compared with the Claude API path of the lesson:
- Bedrock has no Files API: the PDF bytes are sent inline on every call (no file_id,
  no .fichiers.json index, nothing to delete at cleanup).
- Prompt caching uses a `cachePoint` block placed after the document, the Converse
  equivalent of `cache_control` on the document block.
- Server-side `fallbacks` do not exist on Bedrock: a declined request ends the call.
- The cost line is not computed: Bedrock prices depend on the model and the region.

The model id is read from BEDROCK_MODEL_ID (no default, pick one enabled in your
account), the region from the usual AWS settings (AWS_REGION or your profile).
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from schema import SCHEMA_SYNTHESE, Synthese
from service import (
    CONSIGNES,
    MAX_TOKENS,
    PROFILS,
    DemandeRefusee,
    ErreurSynthese,
    SortieInvalide,
    SortieTronquee,
)

# A neutral document name: Bedrock allows only letters, digits, single spaces,
# hyphens, parentheses and square brackets, and the name is visible to the model.
DOCUMENT_NAME = "Document"

AUTH_ERROR_CODES = {"AccessDeniedException", "UnrecognizedClientException", "ExpiredTokenException"}


class MissingModelId(Exception):
    """BEDROCK_MODEL_ID is not set."""


@dataclass
class BedrockResult:
    synthese: Synthese
    model_id: str
    usage: dict
    request_id: str | None


def bedrock_model_id() -> str:
    model_id = os.environ.get("BEDROCK_MODEL_ID", "").strip()
    if not model_id:
        raise MissingModelId("BEDROCK_MODEL_ID")
    return model_id


def make_client():
    import boto3

    return boto3.client("bedrock-runtime")


def build_request(model_id: str, pdf_bytes: bytes, profil: str) -> dict:
    """The Converse request: frozen system prompt, document, cache point, then the profile."""
    return {
        "modelId": model_id,
        "system": [{"text": CONSIGNES}],
        "messages": [{
            "role": "user",
            "content": [
                {"document": {"format": "pdf", "name": DOCUMENT_NAME, "source": {"bytes": pdf_bytes}}},
                {"cachePoint": {"type": "default"}},  # end of the shared prefix
                {"text": PROFILS[profil]},  # varies, not cached
            ],
        }],
        "inferenceConfig": {"maxTokens": MAX_TOKENS},
        "outputConfig": {
            "textFormat": {
                "type": "json_schema",
                "structure": {"jsonSchema": {"name": "synthese", "schema": json.dumps(SCHEMA_SYNTHESE)}},
            },
        },
    }


def synthesize_with_bedrock(chemin: Path, profil: str, client=None) -> BedrockResult:
    """Same three checks as service.synthetiser(): stop reason, Pydantic schema, business rules."""
    if profil not in PROFILS:
        raise ValueError(f"Unknown profile: {profil}")
    model_id = bedrock_model_id()
    client = client or make_client()

    reponse = client.converse(**build_request(model_id, chemin.read_bytes(), profil))

    stop_reason = reponse.get("stopReason")
    if stop_reason in ("content_filtered", "guardrail_intervened"):
        raise DemandeRefusee(f"request declined (stopReason: {stop_reason})")
    if stop_reason in ("max_tokens", "model_context_window_exceeded"):
        raise SortieTronquee("output truncated: raise SYNTHESE_MAX_TOKENS or split the document")
    if stop_reason != "end_turn":
        raise SortieInvalide(f"unexpected stop_reason: {stop_reason}")

    blocs = reponse["output"]["message"]["content"]
    texte = "".join(b["text"] for b in blocs if "text" in b)
    try:
        synthese = Synthese.model_validate_json(texte)
    except ValidationError as e:
        raise SortieInvalide(f"non-conforming output ({e.error_count()} error(s))") from e

    request_id = reponse.get("ResponseMetadata", {}).get("RequestId")
    return BedrockResult(synthese, model_id, reponse.get("usage", {}), request_id)


def main_bedrock(pdf: Path, profil: str, client=None) -> int:
    """Command-line path for MODEL_PROVIDER=bedrock, with the lesson's exit codes."""
    from botocore.exceptions import (
        ClientError,
        EndpointConnectionError,
        NoCredentialsError,
        NoRegionError,
    )

    try:
        resultat = synthesize_with_bedrock(pdf, profil, client)
    except MissingModelId:
        print("Set BEDROCK_MODEL_ID to the id of a model enabled in your account.", file=sys.stderr)
        return 2
    except ErreurSynthese as e:
        print(f"Summary failed: {e}", file=sys.stderr)
        return 3
    except (NoCredentialsError, NoRegionError):
        print("Missing AWS credentials or region (AWS profile, AWS_REGION).", file=sys.stderr)
        return 4
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        message = e.response.get("Error", {}).get("Message", "")
        if code in AUTH_ERROR_CODES:
            print(f"Bedrock access denied ({code}): check your IAM permissions and model access.", file=sys.stderr)
            return 4
        if code == "ThrottlingException":
            print("Bedrock rate limit reached despite retries: try again later.", file=sys.stderr)
            return 5
        print(f"Bedrock error {code}: {message}", file=sys.stderr)
        return 6
    except EndpointConnectionError:
        print("Could not connect to Bedrock.", file=sys.stderr)
        return 7

    u = resultat.usage
    print(resultat.synthese.model_dump_json(indent=2))
    print(f"model: {resultat.model_id} | request-id: {resultat.request_id}", file=sys.stderr)
    print(
        f"usage: input={u.get('inputTokens', 0)} cache_write={u.get('cacheWriteInputTokens', 0)} "
        f"cache_read={u.get('cacheReadInputTokens', 0)} output={u.get('outputTokens', 0)}",
        file=sys.stderr,
    )
    print("estimated cost: not computed (Amazon Bedrock pricing depends on the model and the region)", file=sys.stderr)
    return 0
