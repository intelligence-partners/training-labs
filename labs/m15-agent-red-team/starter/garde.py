# garde.py: the guard module, as at step 4 (no defense yet).
# STARTER: add defenses D2 to D5 at step 6 (TODO markers), and optionally the step 8 filter.
# Identifiers stay in French, as in the lesson (garde means guard).
import json  # noqa: F401  (used by the code you write at step 6)

import outils
from providers import make_client, model_for

DOMAINES_AUTORISES = ("@entreprise.test",)   # D2
PLAFOND_REMBOURSEMENT = 50.0                  # D5


def schemas_actifs(schemas, defenses):
    """D1: in "separation" mode, the reader agent has no tool with side effects."""
    if defenses.get("separation"):
        return [s for s in schemas if s["name"] == "consulter_dossier"]
    return schemas


def appeler(nom, args, demande, defenses):
    # TODO (step 6): insert the defenses here, in this order, each returning
    # {"statut": "refuse", "raison": "..."} instead of running the tool:
    #   D4 "filtrage": for envoyer_email and rembourser, refuse if _parait_injecte(demande, args)
    #   D2 "liste_blanche": refuse an envoyer_email whose destinataire is outside DOMAINES_AUTORISES
    #   D5 "regle_montant": refuse a rembourser whose montant is above PLAFOND_REMBOURSEMENT
    #   D3 "confirmation": for envoyer_email and rembourser, refuse unless _confirme(nom, args)
    return outils.OUTILS[nom](**args)


# The classifier is the second of the two places that talk to a model. Claude API by default;
# on Bedrock, BEDROCK_CLASSIFIER_MODEL_ID (or BEDROCK_MODEL_ID) names the model.
_client = make_client()
MODELE_FILTRE = model_for("claude-haiku-5-5", ("BEDROCK_CLASSIFIER_MODEL_ID", "BEDROCK_MODEL_ID"))


def _confirme(nom, args):
    # TODO (step 6): in automatic test mode, a human approves an action only if the advisor's
    # request mentions it; no legitimate scenario asks for an email or a refund.
    raise NotImplementedError("step 6: _confirme")


_SCHEMA = {"type": "object", "properties": {"injection": {"type": "boolean"}},
           "required": ["injection"], "additionalProperties": False}


def _parait_injecte(demande, args):
    # TODO (step 6): ask MODELE_FILTRE (max_tokens=512, thinking disabled, structured output with
    # _SCHEMA) whether the action matches the advisor's request; return True when it does not,
    # and also when the answer cannot be read (stop_reason other than end_turn).
    raise NotImplementedError("step 6: _parait_injecte")


def ticket_bloque(ticket, defenses):
    """Step 8 (optional): True if the "guardrail" defense is on and the guardrail intervenes."""
    if not defenses.get("guardrail"):
        return False
    # TODO (step 8): call bedrock-runtime apply_guardrail on the ticket (source "INPUT") with the
    # guardrail created by infra/ (BEDROCK_GUARDRAIL_ID, version DRAFT) and return True when the
    # action is GUARDRAIL_INTERVENED.
    raise NotImplementedError("step 8: ticket_bloque")
