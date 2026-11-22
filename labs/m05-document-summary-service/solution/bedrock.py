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
                {"text": PROFILS[profil]},  # varies, outside the cache
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
        raise ValueError(f"Profil inconnu : {profil}")
    model_id = bedrock_model_id()
    client = client or make_client()

    reponse = client.converse(**build_request(model_id, chemin.read_bytes(), profil))

    stop_reason = reponse.get("stopReason")
    if stop_reason in ("content_filtered", "guardrail_intervened"):
        raise DemandeRefusee(f"demande déclinée (stopReason : {stop_reason})")
    if stop_reason in ("max_tokens", "model_context_window_exceeded"):
        raise SortieTronquee("sortie tronquée : relevez SYNTHESE_MAX_TOKENS ou découpez le document")
    if stop_reason != "end_turn":
        raise SortieInvalide(f"stop_reason inattendu : {stop_reason}")

    blocs = reponse["output"]["message"]["content"]
    texte = "".join(b["text"] for b in blocs if "text" in b)
    try:
        synthese = Synthese.model_validate_json(texte)
    except ValidationError as e:
        raise SortieInvalide(f"sortie non conforme ({e.error_count()} erreur(s))") from e

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
        print("Définissez BEDROCK_MODEL_ID avec l'identifiant d'un modèle activé dans votre compte.", file=sys.stderr)
        return 2
    except ErreurSynthese as e:
        print(f"Synthèse impossible : {e}", file=sys.stderr)
        return 3
    except (NoCredentialsError, NoRegionError):
        print("Identifiants ou région AWS absents (profil AWS, AWS_REGION).", file=sys.stderr)
        return 4
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        message = e.response.get("Error", {}).get("Message", "")
        if code in AUTH_ERROR_CODES:
            print(f"Accès Bedrock refusé ({code}) : vérifiez vos droits IAM et l'accès au modèle.", file=sys.stderr)
            return 4
        if code == "ThrottlingException":
            print("Limite de débit Bedrock atteinte malgré les relances : réessayez plus tard.", file=sys.stderr)
            return 5
        print(f"Erreur Bedrock {code} : {message}", file=sys.stderr)
        return 6
    except EndpointConnectionError:
        print("Connexion à Bedrock impossible.", file=sys.stderr)
        return 7

    u = resultat.usage
    print(resultat.synthese.model_dump_json(indent=2))
    print(f"modèle : {resultat.model_id} | request-id : {resultat.request_id}", file=sys.stderr)
    print(
        f"usage : input={u.get('inputTokens', 0)} cache_write={u.get('cacheWriteInputTokens', 0)} "
        f"cache_read={u.get('cacheReadInputTokens', 0)} output={u.get('outputTokens', 0)}",
        file=sys.stderr,
    )
    print("coût estimé : non calculé (tarif Amazon Bedrock propre au modèle et à la région)", file=sys.stderr)
    return 0
