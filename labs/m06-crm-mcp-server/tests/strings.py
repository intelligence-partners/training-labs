"""The user-facing strings of each edition of the lab, as produced by the code.

solution/ and starter/ follow the French lesson (content/outils-mcp/lab.md); solution-en/
and starter-en/ follow the English one (content-en/outils-mcp/lab.md). Tool, resource and
prompt names, identifiers and data keys are the same in both editions.
"""

import os

LANG = "en" if os.environ.get("LAB_TARGET", "solution").endswith("-en") else "fr"

_STRINGS = {
    "fr": {
        "note_added": "Note ajoutée sur Mutuelle Atlantique (C-1002). La fiche compte 1 note(s).",
        "unknown_client": "Aucun client 'C-9999'. Cherchez d'abord l'identifiant avec crm_search_clients.",
        "missing_record": "Aucun client 'C-9999' dans le CRM.",
        "prompt_title": "Préparer un rendez-vous",
        "prompt_start": "Lis la fiche crm://clients/C-1003 puis rédige",
        "instructions_start": "Outils du CRM Orbis",
        "contact_query": "dsi",
        "question": "Quels clients et prospects avons-nous à Lyon ? Donne leur statut.",
        "call": "[appel] orbis.crm_search_clients {'query': 'Lyon'}",
        "result_ok": "[résultat] erreur=False",
        "result_error": "[résultat] erreur=True",
        "stop": "stop_reason : end_turn",
    },
    "en": {
        "note_added": "Note added to Mutuelle Atlantique (C-1002). The record has 1 note(s).",
        "unknown_client": "No customer 'C-9999'. First look up the identifier with crm_search_clients.",
        "missing_record": "No customer 'C-9999' in the CRM.",
        "prompt_title": "Prepare a meeting",
        "prompt_start": "Read the crm://clients/C-1003 record, then write",
        "instructions_start": "Orbis CRM tools",
        "contact_query": "cio",
        "question": "Which customers and prospects do we have in Lyon? Give their status.",
        "call": "[call] orbis.crm_search_clients {'query': 'Lyon'}",
        "result_ok": "[result] error=False",
        "result_error": "[result] error=True",
        "stop": "stop_reason: end_turn",
    },
}

S = _STRINGS[LANG]
