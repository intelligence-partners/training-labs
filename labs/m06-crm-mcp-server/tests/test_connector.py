"""Step 7: appel_connecteur.py, with the Messages API answered by a mock HTTP transport.

The real SDK builds and sends the request; the mock checks it and returns what the API
returns when the MCP connector has called the server: mcp_tool_use and mcp_tool_result
blocks that the script never has to execute itself.
"""

import json
import runpy

import anthropic
import httpx2
import pytest
from conftest import TARGET
from strings import S

SCRIPT = TARGET / "appel_connecteur.py"

API_RESPONSE = {
    "id": "msg_011CTEST",
    "type": "message",
    "role": "assistant",
    "model": "claude-opus-5-5",
    "content": [
        {"type": "mcp_tool_use", "id": "mcptoolu_011C", "name": "crm_search_clients",
         "server_name": "orbis", "input": {"query": "Lyon"}},
        {"type": "mcp_tool_result", "tool_use_id": "mcptoolu_011C", "is_error": False,
         "content": [{"type": "text", "text": '{"id": "C-1001"}'}]},
        {"type": "text", "text": "À Lyon, vous avez un client, Aciéries du Rhône (C-1001), "
                                 "et un prospect, la Clinique du Parc (C-1004)."},
    ],
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {"input_tokens": 2100, "output_tokens": 180},
}


@pytest.fixture
def mocked_api(monkeypatch):
    sent = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(200, json=API_RESPONSE, headers={"request-id": "req_011CTEST"})

    real = anthropic.Anthropic

    def factory(**kwargs):
        return real(api_key="sk-ant-test", max_retries=0,
                    http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)))

    monkeypatch.setattr(anthropic, "Anthropic", factory)
    monkeypatch.setenv("CRM_PUBLIC_URL", "https://orbis-test.trycloudflare.com/")
    monkeypatch.setenv("CRM_TOKEN", "lab-token")
    return sent


def test_request_uses_the_connector_read_only(mocked_api, capsys):
    runpy.run_path(str(SCRIPT), run_name="__main__")

    (request,) = mocked_api
    body = json.loads(request.content)
    assert request.url.path == "/v1/messages"
    assert "mcp-client-2025-11-20" in request.headers["anthropic-beta"]
    assert body["model"] == "claude-opus-5-5"
    assert body["max_tokens"] == 16000
    assert body["mcp_servers"] == [{
        "type": "url",
        "url": "https://orbis-test.trycloudflare.com/mcp",  # trailing slash removed, /mcp added
        "name": "orbis",
        "authorization_token": "lab-token",
    }]
    assert body["tools"] == [{"type": "mcp_toolset", "mcp_server_name": "orbis",
                              "configs": {"crm_add_note": {"enabled": False}}}]
    assert body["messages"][0]["content"] == S["question"]


def test_output_matches_the_lesson(mocked_api, capsys):
    runpy.run_path(str(SCRIPT), run_name="__main__")

    assert capsys.readouterr().out.splitlines() == [
        S["call"],
        S["result_ok"],
        "À Lyon, vous avez un client, Aciéries du Rhône (C-1001), et un prospect, la Clinique du Parc (C-1004).",
        S["stop"],
    ]


def test_missing_public_url_fails_fast(monkeypatch):
    monkeypatch.delenv("CRM_PUBLIC_URL", raising=False)
    with pytest.raises(KeyError, match="CRM_PUBLIC_URL"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
