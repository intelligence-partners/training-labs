# service.py
# Step 4: call Claude and check the response before returning it.
# - The system prompt is frozen and the document carries the cache breakpoint: the
#   system + document prefix is identical from one profile to the next; only the
#   profile instruction, placed after it, varies.
# - fallbacks="default" lets the API retry on another model if a classifier declines.
# - The response goes through three checks: stop_reason, Pydantic schema, business rules.
import os
from dataclasses import dataclass

import anthropic
from anthropic.types.beta import BetaUsage
from pydantic import ValidationError

from schema import SCHEMA_SYNTHESE, Synthese

MODELE = "claude-opus-5-5"
MAX_TOKENS = int(os.environ.get("SYNTHESE_MAX_TOKENS", "16000"))
# Opus 5.5 pricing as of October 27, 2026, in dollars per million tokens.
PRIX = {"input": 4.00, "cache_write_5m": 5.00, "cache_read": 0.20, "output": 20.00}

client = anthropic.Anthropic(max_retries=4, timeout=300.0)

CONSIGNES = """You are an analyst at a consulting firm. You write summaries of business
documents for decision-makers who do not have time to read them.

Rules:
- Rely only on the document provided. Add no outside information.
- Copy figures exactly as they appear in the document, with their unit.
- If a page cannot be identified, set page to null. Never invent a page number.
- Order key points from most to least important, between three and seven.
- Risks are those the document mentions or makes obvious; one sentence each.
- Open questions are the important pieces of information the document does not give.
- Write in English, in short sentences, without pleasantries."""

PROFILS = {
    "direction": "Reader profile: executive management. Focus on financial stakes, decisions to make and major risks.",
    "juridique": "Reader profile: legal department. Focus on commitments, obligations, deadlines, sensitive clauses and areas of ambiguity.",
    "operationnel": "Reader profile: operations manager. Focus on actions, timelines, required resources and dependencies.",
}


class ErreurSynthese(Exception):
    """A summary could not be produced reliably."""


class DemandeRefusee(ErreurSynthese):
    pass


class SortieTronquee(ErreurSynthese):
    pass


class SortieInvalide(ErreurSynthese):
    pass


@dataclass
class Resultat:
    synthese: Synthese
    modele: str
    usage: BetaUsage
    request_id: str | None


def cout_estime(usage: BetaUsage) -> float:
    return (
        usage.input_tokens * PRIX["input"]
        + (usage.cache_creation_input_tokens or 0) * PRIX["cache_write_5m"]
        + (usage.cache_read_input_tokens or 0) * PRIX["cache_read"]
        + usage.output_tokens * PRIX["output"]
    ) / 1_000_000


def synthetiser(file_id: str, profil: str) -> Resultat:
    if profil not in PROFILS:
        raise ValueError(f"Unknown profile: {profil}")

    reponse = client.beta.messages.create(
        model=MODELE,
        max_tokens=MAX_TOKENS,
        system=CONSIGNES,
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": SCHEMA_SYNTHESE},
        },
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {"type": "file", "file_id": file_id},
                    "title": "Document to summarize",
                    "cache_control": {"type": "ephemeral"},  # end of the shared prefix
                },
                {"type": "text", "text": PROFILS[profil]},  # varies, not cached
            ],
        }],
        fallbacks="default",
        betas=["server-side-fallback-2026-07-01"],
    )

    # 1. stop_reason first: a refusal or a truncation is never parsed.
    if reponse.stop_reason == "refusal":
        categorie = reponse.stop_details.category if reponse.stop_details else None
        raise DemandeRefusee(f"request declined (category: {categorie})")
    if reponse.stop_reason in ("max_tokens", "model_context_window_exceeded"):
        raise SortieTronquee("output truncated: raise SYNTHESE_MAX_TOKENS or split the document")
    if reponse.stop_reason != "end_turn":
        raise SortieInvalide(f"unexpected stop_reason: {reponse.stop_reason}")

    # 2. Then the schema and the business rules, on the client side.
    texte = "".join(b.text for b in reponse.content if b.type == "text")
    try:
        synthese = Synthese.model_validate_json(texte)
    except ValidationError as e:
        raise SortieInvalide(f"non-conforming output ({e.error_count()} error(s))") from e

    return Resultat(synthese, reponse.model, reponse.usage, reponse._request_id)
