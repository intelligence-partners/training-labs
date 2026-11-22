"""MCP server for the fictitious "Orbis" CRM: customer search, notes, customer record."""

# Step 2: the MCP server. The same file serves over stdio (default) and Streamable HTTP
# (--http). Over HTTP, a static token read from CRM_TOKEN protects access: a lab shortcut,
# to be replaced with OAuth 2.1 in production.

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
        if TOKEN and token == TOKEN:
            return AccessToken(token=token, client_id="lab", scopes=["crm"], resource=RESOURCE)
        return None


options = {}
if TOKEN:
    options = {
        "token_verifier": JetonStatique(),
        "auth": AuthSettings(
            issuer_url=AnyHttpUrl("https://auth.example.com"),
            resource_server_url=AnyHttpUrl(RESOURCE),
            required_scopes=["crm"],
            validate_token_resource=True,
        ),
    }

mcp = MCPServer(
    "orbis-crm",
    instructions="Orbis CRM tools: search customers, read a record, add a follow-up note.",
    **options,
)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
def crm_search_clients(
    query: Annotated[str, Field(description="Name, city or contact person to search for, case-insensitive. Empty string to list everything.")],
    secteur: Annotated[Secteur | None, Field(description="Optional filter on the business sector.")] = None,
    limit: Annotated[int, Field(ge=1, le=20, description="Maximum number of results.")] = 5,
) -> list[dict]:
    """Searches customers and prospects in the Orbis CRM. Use it as soon as the user
    mentions a company, a city or a contact person, before reading a record or adding
    a note. Returns the identifier (C-XXXX), name, city, sector and status, without
    the notes: read the crm://clients/{id} resource for details."""
    q = query.strip().lower()
    trouves = [
        {k: c[k] for k in ("id", "nom", "ville", "secteur", "statut")}
        for c in charger()["clients"]
        if (not q or q in c["nom"].lower() or q in c["ville"].lower() or q in c["interlocuteur"].lower())
        and (secteur is None or c["secteur"] == secteur)
    ]
    return trouves[:limit]


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False))
def crm_add_note(
    client_id: Annotated[str, Field(description="Customer identifier, in the C-XXXX format, obtained with crm_search_clients.")],
    texte: Annotated[str, Field(description="Content of the note, factual, one to three sentences.")],
    auteur: Annotated[str, Field(description="First name of the person writing the note.")],
) -> str:
    """Adds a follow-up note dated today to a customer record. Only call this tool if
    the user explicitly asks to save a note: the write is permanent. Returns a
    confirmation with the number of notes on the record."""
    data = charger()
    for c in data["clients"]:
        if c["id"] == client_id:
            c["notes"].append({"date": date.today().isoformat(), "auteur": auteur, "texte": texte})
            sauver(data)
            return f"Note added to {c['nom']} ({client_id}). The record has {len(c['notes'])} note(s)."
    raise ToolError(f"No customer {client_id!r}. First look up the identifier with crm_search_clients.")


@mcp.resource("crm://clients/{client_id}", mime_type="application/json")
def fiche_client(client_id: str) -> dict:
    """Full customer record: details, revenue, contact person and notes."""
    for c in charger()["clients"]:
        if c["id"] == client_id:
            return c
    raise ResourceNotFoundError(f"No customer {client_id!r} in the CRM.")


@mcp.prompt(title="Prepare a meeting")
def preparer_rendez_vous(
    client_id: Annotated[str, Field(description="Customer identifier, in the C-XXXX format.")],
) -> str:
    """Prepares a meeting brief from the customer record."""
    return (
        f"Read the crm://clients/{client_id} record, then write a meeting brief: "
        "context in three bullets, note history, two questions to ask."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Serve over Streamable HTTP instead of stdio")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.http:
        public_host = AnyHttpUrl(PUBLIC_URL).host
        mcp.run(
            transport="streamable-http",
            port=args.port,
            json_response=True,  # plain JSON responses, no SSE stream
            transport_security=TransportSecuritySettings(
                allowed_hosts=["127.0.0.1:*", "localhost:*", public_host, f"{public_host}:*"],
            ),
        )
    else:
        mcp.run()
