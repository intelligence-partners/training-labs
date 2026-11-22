"""Serveur MCP du CRM fictif « Orbis » : recherche de clients, notes, fiche client."""

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
    instructions="Outils du CRM Orbis : rechercher des clients, lire une fiche, ajouter une note de suivi.",
    **options,
)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
def crm_search_clients(
    query: Annotated[str, Field(description="Nom, ville ou interlocuteur à chercher, insensible à la casse. Chaîne vide pour tout lister.")],
    secteur: Annotated[Secteur | None, Field(description="Filtre facultatif sur le secteur d'activité.")] = None,
    limit: Annotated[int, Field(ge=1, le=20, description="Nombre maximal de résultats.")] = 5,
) -> list[dict]:
    """Cherche des clients et prospects dans le CRM Orbis. À utiliser dès que l'utilisateur
    évoque une entreprise, une ville ou un interlocuteur, avant de lire une fiche ou d'ajouter
    une note. Renvoie l'identifiant (C-XXXX), le nom, la ville, le secteur et le statut,
    sans les notes : lisez la ressource crm://clients/{id} pour le détail."""
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
    client_id: Annotated[str, Field(description="Identifiant du client, au format C-XXXX, obtenu avec crm_search_clients.")],
    texte: Annotated[str, Field(description="Contenu de la note, factuel, une à trois phrases.")],
    auteur: Annotated[str, Field(description="Prénom de la personne qui rédige la note.")],
) -> str:
    """Ajoute une note de suivi datée du jour sur la fiche d'un client. N'appelez cet outil
    que si l'utilisateur demande explicitement d'enregistrer une note : l'écriture est
    définitive. Renvoie une confirmation avec le nombre de notes de la fiche."""
    data = charger()
    for c in data["clients"]:
        if c["id"] == client_id:
            c["notes"].append({"date": date.today().isoformat(), "auteur": auteur, "texte": texte})
            sauver(data)
            return f"Note ajoutée sur {c['nom']} ({client_id}). La fiche compte {len(c['notes'])} note(s)."
    raise ToolError(f"Aucun client {client_id!r}. Cherchez d'abord l'identifiant avec crm_search_clients.")


@mcp.resource("crm://clients/{client_id}", mime_type="application/json")
def fiche_client(client_id: str) -> dict:
    """Fiche complète d'un client : coordonnées, chiffre d'affaires, interlocuteur et notes."""
    for c in charger()["clients"]:
        if c["id"] == client_id:
            return c
    raise ResourceNotFoundError(f"Aucun client {client_id!r} dans le CRM.")


@mcp.prompt(title="Préparer un rendez-vous")
def preparer_rendez_vous(
    client_id: Annotated[str, Field(description="Identifiant du client, au format C-XXXX.")],
) -> str:
    """Prépare une fiche de rendez-vous à partir de la fiche client."""
    return (
        f"Lis la fiche crm://clients/{client_id} puis rédige une préparation de rendez-vous : "
        "contexte en trois puces, historique des notes, deux questions à poser."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Servir en Streamable HTTP au lieu de stdio")
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
