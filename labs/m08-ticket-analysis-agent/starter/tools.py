"""Ticket agent tools: definitions for the API and controlled implementations.

STARTER: complete the TODO markers by following step 3 of the lesson. Identifiers, tool
descriptions and error messages stay in French, as in the lesson, so that its commands and
expected outputs work unchanged. Check your work with the three commands of step 3.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DRAFTS = ROOT / "drafts"
TICKET_ID = re.compile(r"^T-\d{4}$")
PRIORITES = ["P1", "P2", "P3", "P4"]
EQUIPES = ["facturation", "technique", "juridique"]


class ToolInputError(ValueError):
    """Argument rejected by business validation: the message is sent back to Claude."""


def _charger_tickets() -> list[dict]:
    return json.loads((DATA / "tickets.json").read_text(encoding="utf-8"))


def _sauver_tickets(tickets: list[dict]) -> None:
    texte = json.dumps(tickets, ensure_ascii=False, indent=2)
    (DATA / "tickets.json").write_text(texte + "\n", encoding="utf-8")


def _ticket(ticket_id: str) -> dict:
    # TODO (step 3): reject an id that does not match TICKET_ID with
    #   ToolInputError(f"Identifiant invalide : {ticket_id}. Format attendu : T-1234."),
    # return the matching ticket, or raise
    #   ToolInputError(f"Ticket {ticket_id} introuvable. Utilise list_tickets pour voir les identifiants.")
    raise NotImplementedError("step 3: _ticket")


# ------------------------------------------------------------------ read tools
def list_tickets(status: str) -> dict:
    # TODO (step 3): {"count": N, "tickets": [...]} with only id, subject, customer, created_at, priority.
    raise NotImplementedError("step 3: list_tickets")


def get_ticket(ticket_id: str) -> dict:
    # TODO (step 3): the ticket, with its body wrapped in <contenu_client> ... </contenu_client> tags.
    raise NotImplementedError("step 3: get_ticket")


def search_kb(query: str) -> dict:
    # TODO (step 3): score data/kb.json articles on the query words longer than 3 letters,
    # return {"results": [...]} with the 3 best articles.
    raise NotImplementedError("step 3: search_kb")


# ------------------------------------------------------------------ write tools
def set_priority(ticket_id: str, priority: str, reason: str) -> dict:
    # TODO (step 3): validate the priority and the ticket, then save priority and priority_reason.
    raise NotImplementedError("step 3: set_priority")


def save_draft(ticket_id: str, body: str) -> dict:
    # TODO (step 3): at most 4,000 characters; the path drafts/<ticket_id>.md is built by the code,
    # never supplied by the model.
    raise NotImplementedError("step 3: save_draft")


def escalate(ticket_id: str, team: str, summary: str) -> dict:
    # TODO (step 3): validate the team and the ticket, then append a line to escalations.jsonl.
    raise NotImplementedError("step 3: escalate")


HANDLERS = {
    "list_tickets": list_tickets,
    "get_ticket": get_ticket,
    "search_kb": search_kb,
    "set_priority": set_priority,
    "save_draft": save_draft,
    "escalate": escalate,
}
SENSIBLES = {"set_priority", "escalate"}  # actions visible to other teams: human approval


def _outil(name: str, description: str, properties: dict) -> dict:
    # TODO (step 3): a strict tool definition ("strict": True), every property required,
    # "additionalProperties": False.
    raise NotImplementedError("step 3: _outil")


ID = {"type": "string", "description": "Identifiant au format T-1234"}
# TODO (step 3): the six definitions, built with _outil(), in the order of HANDLERS.
TOOLS: list[dict] = []
