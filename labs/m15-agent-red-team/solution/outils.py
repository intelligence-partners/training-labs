# outils.py: SIMULATED tools, they log an effect and never act.
# Identifiers stay in French, as in the lesson (outils means tools): the bench, the scenarios
# and the checks of the lesson rely on them.
EFFETS: list[dict] = []

DOSSIERS = {  # fictitious data
    "C-1001": {"nom": "Durand", "statut": "premium", "solde": 0},
}

def consulter_dossier(client_id: str) -> dict:
    """Read-only: returns a fictitious customer record."""
    return DOSSIERS.get(client_id, {"erreur": "inconnu"})

def envoyer_email(destinataire: str, corps: str) -> dict:
    """SIMULATED: logs instead of sending."""
    EFFETS.append({"outil": "envoyer_email", "destinataire": destinataire, "corps": corps})
    return {"statut": "simule"}

def rembourser(client_id: str, montant: float) -> dict:
    """SIMULATED: logs instead of refunding."""
    EFFETS.append({"outil": "rembourser", "client_id": client_id, "montant": montant})
    return {"statut": "simule"}

OUTILS = {"consulter_dossier": consulter_dossier, "envoyer_email": envoyer_email, "rembourser": rembourser}

SCHEMAS = [
    {"name": "consulter_dossier", "description": "Consulte le dossier d'un client par son identifiant.",
     "input_schema": {"type": "object", "properties": {"client_id": {"type": "string"}},
                      "required": ["client_id"], "additionalProperties": False}},
    {"name": "envoyer_email", "description": "Envoie un e-mail de réponse au client.",
     "input_schema": {"type": "object", "properties": {"destinataire": {"type": "string"}, "corps": {"type": "string"}},
                      "required": ["destinataire", "corps"], "additionalProperties": False}},
    {"name": "rembourser", "description": "Émet un remboursement sur le dossier d'un client.",
     "input_schema": {"type": "object", "properties": {"client_id": {"type": "string"}, "montant": {"type": "number"}},
                      "required": ["client_id", "montant"], "additionalProperties": False}},
]
