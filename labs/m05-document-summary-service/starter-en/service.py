# service.py
# Step 4: call Claude and check the response before returning it.
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
    # TODO(step 4): input, cache write, cache read and output tokens times PRIX, divided by one million.
    # The cache fields can be None: count them as 0.
    raise NotImplementedError("TODO(step 4): cout_estime")


def synthetiser(file_id: str, profil: str) -> Resultat:
    if profil not in PROFILS:
        raise ValueError(f"Unknown profile: {profil}")

    # TODO(step 4a): call client.beta.messages.create with
    # - model=MODELE, max_tokens=MAX_TOKENS, system=CONSIGNES (frozen system prompt)
    # - output_config: effort "medium" and format {"type": "json_schema", "schema": SCHEMA_SYNTHESE}
    # - one user message: the document block (source {"type": "file", "file_id": ...},
    #   title "Document to summarize", cache_control {"type": "ephemeral"}: end of the shared prefix),
    #   then a text block with PROFILS[profil] (varies, outside the cache)
    # - fallbacks="default" and betas=["server-side-fallback-2026-07-01"]

    # TODO(step 4b): stop_reason first, a refusal or a truncation is never parsed:
    # - "refusal" -> DemandeRefusee(f"request declined (category: {categorie})"), category from stop_details
    # - "max_tokens" or "model_context_window_exceeded" ->
    #   SortieTronquee("output truncated: raise SYNTHESE_MAX_TOKENS or split the document")
    # - anything else than "end_turn" -> SortieInvalide(f"unexpected stop_reason: {reponse.stop_reason}")

    # TODO(step 4c): join the text blocks, validate with Synthese.model_validate_json, turn a
    # ValidationError into SortieInvalide(f"non-conforming output ({e.error_count()} error(s))"),
    # then return Resultat(synthese, reponse.model, reponse.usage, reponse._request_id).
    raise NotImplementedError("TODO(step 4): synthetiser")

