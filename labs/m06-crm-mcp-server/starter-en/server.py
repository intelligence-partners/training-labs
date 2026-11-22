"""MCP server for the fictitious "Orbis" CRM: customer search, notes, customer record."""

# Step 2: the MCP server. The same file serves over stdio (default) and Streamable HTTP
# (--http). Over HTTP, a static token read from CRM_TOKEN protects access: a lab shortcut,
# to be replaced with OAuth 2.1 in production.
#
# The starter already runs (`python server.py` waits silently on stdio) and registers the
# four primitives, so MCP Inspector lists them while you fill in the TODOs.

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field

from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

DATA_FILE = Path(os.environ.get("CRM_DATA", Path(__file__).parent / "crm_data.json"))
PUBLIC_URL = os.environ.get("CRM_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")
RESOURCE = f"{PUBLIC_URL}/mcp"
TOKEN = os.environ.get("CRM_TOKEN")

Secteur = Literal["industrie", "assurance", "logistique", "sante", "finance", "agroalimentaire"]


def charger() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def sauver(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class JetonStatique(TokenVerifier):
    """Demo verifier: a single token, read from CRM_TOKEN. Never in production."""

    async def verify_token(self, token: str) -> AccessToken | None:
        # TODO(step 5): accept only TOKEN. Return
        # AccessToken(token=token, client_id="lab", scopes=["crm"], resource=RESOURCE), else None.
        return None


options = {}
if TOKEN:
    # TODO(step 5): protect the HTTP server: token_verifier=JetonStatique() and
    # auth=AuthSettings(issuer_url=AnyHttpUrl("https://auth.example.com"),
    #                   resource_server_url=AnyHttpUrl(RESOURCE), required_scopes=["crm"],
    #                   validate_token_resource=True)
    options = {}

mcp = MCPServer(
    "orbis-crm",
    instructions="Orbis CRM tools: search customers, read a record, add a follow-up note.",
    **options,
)


# TODO(step 2): declare the tool read-only with
# annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False)
@mcp.tool()
def crm_search_clients(
    query: Annotated[str, Field(description="Name, city or contact person to search for, case-insensitive. Empty string to list everything.")],
    secteur: Annotated[Secteur | None, Field(description="Optional filter on the business sector.")] = None,
    # TODO(step 2): bound limit between 1 and 20 with Field(ge=..., le=...)
    limit: Annotated[int, Field(description="Maximum number of results.")] = 5,
) -> list[dict]:
    """TODO(step 2): a description that says when to call the tool and what it returns
    (identifier C-XXXX, name, city, sector, status, without the notes)."""
    # TODO(step 2): case-insensitive search on nom, ville and interlocuteur (empty query lists
    # everything), optional filter on secteur, return at most `limit` dicts with the keys
    # id, nom, ville, secteur, statut.
    raise ToolError("TODO(step 2): crm_search_clients")


# TODO(step 2): annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False)
@mcp.tool()
def crm_add_note(
    client_id: Annotated[str, Field(description="Customer identifier, in the C-XXXX format, obtained with crm_search_clients.")],
    texte: Annotated[str, Field(description="Content of the note, factual, one to three sentences.")],
    auteur: Annotated[str, Field(description="First name of the person writing the note.")],
) -> str:
    """TODO(step 2): a description that says to call the tool only on an explicit request."""
    # TODO(step 2): append {"date": date.today().isoformat(), "auteur": ..., "texte": ...} to the
    # client's notes, save, and return
    # f"Note added to {nom} ({client_id}). The record has {n} note(s)."
    # Unknown client: raise ToolError with a message that says how to fix the call
    # (look the identifier up with crm_search_clients first).
    raise ToolError("TODO(step 2): crm_add_note")


@mcp.resource("crm://clients/{client_id}", mime_type="application/json")
def fiche_client(client_id: str) -> dict:
    """Full customer record: details, revenue, contact person and notes."""
    # TODO(step 2): return the client's full record; unknown id -> ResourceNotFoundError.
    raise ResourceNotFoundError(f"TODO(step 2): fiche_client({client_id})")


@mcp.prompt(title="Prepare a meeting")
def preparer_rendez_vous(
    client_id: Annotated[str, Field(description="Customer identifier, in the C-XXXX format.")],
) -> str:
    """Prepares a meeting brief from the customer record."""
    # TODO(step 2): ask to read crm://clients/{client_id}, then write a meeting brief:
    # context in three bullets, history of the notes, two questions to ask.
    return f"TODO(step 2): preparer_rendez_vous({client_id})"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Serve over Streamable HTTP instead of stdio")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.http:
        public_host = AnyHttpUrl(PUBLIC_URL).host
        # TODO(step 5): run with transport="streamable-http", port=args.port, json_response=True
        # (plain JSON, no SSE: quick tunnels do not support it) and
        # transport_security=TransportSecuritySettings(allowed_hosts=[...]) listing
        # "127.0.0.1:*", "localhost:*", public_host and f"{public_host}:*".
        raise SystemExit("TODO(step 5): HTTP transport")
    else:
        mcp.run()
