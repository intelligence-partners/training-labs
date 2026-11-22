"""The user-facing strings of each edition of the lab, as printed by the code.

solution/ and starter/ follow the French lesson (content/api-claude/lab.md); solution-en/
and starter-en/ follow the English one (content-en/api-claude/lab.md). Identifiers are the
same in both editions; only prompts and messages differ.
"""

import os

TARGET_NAME = os.environ.get("LAB_TARGET", "solution")
LANG = "en" if TARGET_NAME.endswith("-en") else "fr"

_STRINGS = {
    "fr": {
        "not_pdf": "Fichier PDF introuvable.",
        "failed": "Synthèse impossible : ",
        "truncated": "sortie tronquée : relevez SYNTHESE_MAX_TOKENS ou découpez le document",
        "declined": "demande déclinée",
        "declined_cyber": r"demande déclinée \(catégorie : cyber\)",
        "unexpected": "stop_reason inattendu : ",
        "invalid": r"sortie non conforme \({n} erreur\(s\)\)",
        "invalid_prefix": "sortie non conforme",
        "unknown_profile": "Profil inconnu : ",
        "document_title": "Document à synthétiser",
        "model": "modèle : {model} | request-id : {request_id}",
        "usage": "usage : input={i} cache_write={w} cache_read={r} output={o}",
        "cost": "coût estimé (tarif Opus 5.5) : {cost} $",
        "auth": "Clé d'API absente ou invalide (ANTHROPIC_API_KEY).",
        "rate": "Limite de débit atteinte malgré les relances : réessayez plus tard.",
        "api_error": "Erreur API {status} : ",
        "connection": "Connexion à l'API impossible.",
        "exit_echo": 'echo "code de sortie : $?"',
        "exit_line": "code de sortie : {code}",
        "ts_usage": "modèle : claude-opus-5-5 | usage : input=72 cache_write=61840 cache_read=0 output=2914",
        "profile_legal": "juridique",
        "profile_operations": "opérationnel",
    },
    "en": {
        "not_pdf": "PDF file not found.",
        "failed": "Summary failed: ",
        "truncated": "output truncated: raise SYNTHESE_MAX_TOKENS or split the document",
        "declined": "request declined",
        "declined_cyber": r"request declined \(category: cyber\)",
        "unexpected": "unexpected stop_reason: ",
        "invalid": r"non-conforming output \({n} error\(s\)\)",
        "invalid_prefix": "non-conforming output",
        "unknown_profile": "Unknown profile: ",
        "document_title": "Document to summarize",
        "model": "model: {model} | request-id: {request_id}",
        "usage": "usage: input={i} cache_write={w} cache_read={r} output={o}",
        "cost": "estimated cost (Opus 5.5 pricing): ${cost}",
        "auth": "Missing or invalid API key (ANTHROPIC_API_KEY).",
        "rate": "Rate limit reached despite retries: try again later.",
        "api_error": "API error {status}: ",
        "connection": "Could not connect to the API.",
        "exit_echo": 'echo "exit code: $?"',
        "exit_line": "exit code: {code}",
        "ts_usage": "model: claude-opus-5-5 | usage: input=72 cache_write=61840 cache_read=0 output=2914",
        "profile_legal": "legal",
        "profile_operations": "operations",
    },
}

S = _STRINGS[LANG]
USAGE_FIRST = S["usage"].format(i=72, w=61840, r=0, o=2914)
USAGE_SECOND = S["usage"].format(i=74, w=0, r=61840, o=2950)
COST_FIRST = S["cost"].format(cost="0.3678")
COST_SECOND = S["cost"].format(cost="0.0717")
TRUNCATED_LINE = S["failed"] + S["truncated"]


def model_line(model: str, request_id: str) -> str:
    return S["model"].format(model=model, request_id=request_id)
