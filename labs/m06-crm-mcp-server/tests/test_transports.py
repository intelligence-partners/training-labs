"""Steps 3, 5 and 6: the server as the Inspector and curl see it, over stdio and over HTTP.

The Python MCP client plays the part of MCP Inspector: same server command, same calls.
The same client also drives the TypeScript variant, which is the point of an open protocol:
one client, two server implementations.
"""

import json
import os
import subprocess
import sys

import httpx2
import pytest
from conftest import TARGET, TS_DIR, TSX, free_port, require_node, wait_for_port

from mcp import Client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client

pytestmark = pytest.mark.anyio
TOKEN = "lab-token-for-tests"


async def check_lyon(client: Client) -> None:
    result = await client.call_tool("crm_search_clients", {"query": "lyon"})
    text = "\n".join(block.text for block in result.content)
    assert result.is_error is False
    assert "C-1001" in text and "C-1004" in text and "C-1003" not in text
    fiche = await client.read_resource("crm://clients/C-1003")
    assert json.loads(fiche.contents[0].text)["ville"] == "Grenoble"


# -- step 3: stdio, the command given to the Inspector and to `claude mcp add` ------------------

async def test_python_server_over_stdio(crm_file):
    params = StdioServerParameters(command=sys.executable, args=[str(TARGET / "server.py")],
                                   env={"CRM_DATA": str(crm_file)})
    async with Client(params) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert names == {"crm_search_clients", "crm_add_note"}
        await check_lyon(client)
        over = await client.call_tool("crm_search_clients", {"query": "", "limit": 99})
        assert over.is_error is True


# -- steps 5 and 6: Streamable HTTP behind a static token --------------------------------------

@pytest.fixture
def http_server(crm_file):
    port = free_port()
    env = {**os.environ, "CRM_DATA": str(crm_file), "CRM_TOKEN": TOKEN,
           "CRM_PUBLIC_URL": "https://orbis-test.trycloudflare.com"}
    process = subprocess.Popen([sys.executable, str(TARGET / "server.py"), "--http", "--port", str(port)],
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        wait_for_port(port, process)
        yield f"http://127.0.0.1:{port}"
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_request_without_token_is_401(http_server):
    response = httpx2.post(f"{http_server}/mcp", headers={"Content-Type": "application/json"}, content="{}")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == (
        'Bearer error="invalid_token", error_description="Authentication required", '
        'resource_metadata="https://orbis-test.trycloudflare.com/.well-known/oauth-protected-resource/mcp"'
    )
    assert response.json() == {"error": "invalid_token", "error_description": "Authentication required"}


def test_protected_resource_metadata(http_server):
    metadata = httpx2.get(f"{http_server}/.well-known/oauth-protected-resource/mcp").json()
    assert metadata["resource"] == "https://orbis-test.trycloudflare.com/mcp"
    assert metadata["authorization_servers"] == ["https://auth.example.com/"]
    assert metadata["scopes_supported"] == ["crm"]


def test_wrong_token_is_401(http_server):
    response = httpx2.post(f"{http_server}/mcp", headers={"Authorization": "Bearer wrong"}, content="{}")
    assert response.status_code == 401


def test_unknown_host_is_rejected_public_host_is_allowed(http_server):
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                             "clientInfo": {"name": "test", "version": "1"}}}
    evil = httpx2.post(f"{http_server}/mcp", json=initialize, headers={**headers, "Host": "evil.example.com"})
    public = httpx2.post(f"{http_server}/mcp", json=initialize,
                         headers={**headers, "Host": "orbis-test.trycloudflare.com"})

    assert evil.status_code == 421  # DNS rebinding protection
    assert public.status_code == 200
    assert public.headers["content-type"].startswith("application/json")  # json_response=True: no SSE
    assert public.json()["result"]["serverInfo"]["name"] == "orbis-crm"


async def test_client_with_token_lists_and_calls(http_server):
    http = httpx2.AsyncClient(headers={"Authorization": f"Bearer {TOKEN}"})
    async with http, Client(streamable_http_client(f"{http_server}/mcp", http_client=http)) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        assert tools["crm_search_clients"].output_schema is not None
        assert tools["crm_search_clients"].annotations.read_only_hint is True
        await check_lyon(client)


# -- TypeScript variant of the server -----------------------------------------------------------

async def test_typescript_server_over_stdio(crm_file):
    require_node()
    params = StdioServerParameters(command=str(TSX), args=[str(TS_DIR / "src" / "stdio.ts")],
                                   env={"CRM_DATA": str(crm_file)}, cwd=str(TS_DIR))
    async with Client(params) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert names == {"crm_search_clients", "crm_add_note"}
        await check_lyon(client)
        note = await client.call_tool("crm_add_note", {"client_id": "C-1002", "texte": "Rappel jeudi.", "auteur": "Léa"})
        assert note.is_error is False
        missing = await client.call_tool("crm_add_note", {"client_id": "C-9999", "texte": "x", "auteur": "Léa"})
        assert missing.is_error is True
    saved = json.loads(crm_file.read_text(encoding="utf-8"))
    assert next(c for c in saved["clients"] if c["id"] == "C-1002")["notes"][0]["auteur"] == "Léa"


async def test_typescript_server_over_http(crm_file):
    require_node()
    port = 3000  # fixed in src/http.ts, as in the lesson
    env = {**os.environ, "CRM_DATA": str(crm_file), "CRM_TOKEN": TOKEN}
    process = subprocess.Popen([str(TSX), "src/http.ts"], cwd=TS_DIR, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        try:
            wait_for_port(port, process)
        except RuntimeError as error:
            if "EADDRINUSE" in str(error):
                pytest.skip("port 3000 is already in use on this machine")
            raise
        url = f"http://127.0.0.1:{port}/mcp"
        assert httpx2.post(url, json={}).status_code == 401
        http = httpx2.AsyncClient(headers={"Authorization": f"Bearer {TOKEN}"})
        async with http, Client(streamable_http_client(url, http_client=http)) as client:
            await check_lyon(client)
    finally:
        process.terminate()
        process.wait(timeout=10)
