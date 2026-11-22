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
# Opus 5.5 prices on 27 October 2026, in dollars per million tokens.
PRIX = {"input": 4.00, "cache_write_5m": 5.00, "cache_read": 0.20, "output": 20.00}

client = anthropic.Anthropic(max_retries=4, timeout=300.0)

CONSIGNES = """Tu es analyste dans un cabinet de conseil. Tu produis des synthèses de documents
d'entreprise destinées à des décideurs qui n'ont pas le temps de les lire.

Règles :
- Tu t'appuies uniquement sur le document fourni. Tu n'ajoutes aucune information extérieure.
- Les chiffres sont recopiés tels qu'ils figurent dans le document, avec leur unité.
- Si une page n'est pas identifiable, la page vaut null. Tu n'inventes jamais un numéro de page.
- Les points clés vont du plus important au moins important, entre trois et sept.
- Les risques sont ceux que le document mentionne ou qu'il rend évidents ; une phrase chacun.
- Les questions ouvertes sont les informations importantes que le document ne donne pas.
- Tu écris en français, phrases courtes, sans formule de politesse."""

PROFILS = {
    "direction": "Profil de lecteur : direction générale. Priorité aux enjeux financiers, aux décisions à prendre et aux risques majeurs.",
    "juridique": "Profil de lecteur : direction juridique. Priorité aux engagements, obligations, échéances, clauses sensibles et zones d'ambiguïté.",
    "operationnel": "Profil de lecteur : responsable opérationnel. Priorité aux actions, délais, ressources nécessaires et dépendances.",
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
        raise ValueError(f"Profil inconnu : {profil}")

    # TODO(step 4a): call client.beta.messages.create with
    # - model=MODELE, max_tokens=MAX_TOKENS, system=CONSIGNES (frozen system prompt)
    # - output_config: effort "medium" and format {"type": "json_schema", "schema": SCHEMA_SYNTHESE}
    # - one user message: the document block (source {"type": "file", "file_id": ...},
    #   title "Document à synthétiser", cache_control {"type": "ephemeral"}: end of the shared prefix),
    #   then a text block with PROFILS[profil] (varies, outside the cache)
    # - fallbacks="default" and betas=["server-side-fallback-2026-07-01"]

    # TODO(step 4b): stop_reason first, a refusal or a truncation is never parsed:
    # - "refusal" -> DemandeRefusee(f"demande déclinée (catégorie : {categorie})"), category from stop_details
    # - "max_tokens" or "model_context_window_exceeded" ->
    #   SortieTronquee("sortie tronquée : relevez SYNTHESE_MAX_TOKENS ou découpez le document")
    # - anything else than "end_turn" -> SortieInvalide(f"stop_reason inattendu : {reponse.stop_reason}")

    # TODO(step 4c): join the text blocks, validate with Synthese.model_validate_json, turn a
    # ValidationError into SortieInvalide(f"sortie non conforme ({e.error_count()} erreur(s))"),
    # then return Resultat(synthese, reponse.model, reponse.usage, reponse._request_id).
    raise NotImplementedError("TODO(step 4): synthetiser")

