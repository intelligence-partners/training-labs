"""Optional provider switch: the MCP client loop with Amazon Bedrock Converse.

botocore's Stubber answers converse() and validates every request against the
bedrock-runtime service model; the MCP side is the real server, in memory.
"""

import copy
import runpy

import boto3
import pytest
from botocore.stub import ANY, Stubber
from conftest import TARGET
from strings import S

if not (TARGET / "bedrock_mcp_client.py").exists():
    pytest.skip("the optional Bedrock client is in solution/", allow_module_level=True)

from mcp import Client  # noqa: E402

import bedrock_mcp_client  # noqa: E402
import server  # noqa: E402

MODEL_ID = "test.model-id-from-env"


def converse(content: list, stop_reason: str) -> dict:
    return {
        "output": {"message": {"role": "assistant", "content": content}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 900, "outputTokens": 60, "totalTokens": 960},
        "metrics": {"latencyMs": 800},
    }


@pytest.fixture
def stubbed():
    client = boto3.client("bedrock-runtime", region_name="eu-west-3",
                          aws_access_key_id="testing", aws_secret_access_key="testing")
    with Stubber(client) as stubber:
        yield client, stubber


@pytest.mark.anyio
async def test_tool_loop(crm_file, stubbed):
    bedrock, stubber = stubbed
    first = {"modelId": MODEL_ID, "messages": ANY, "toolConfig": ANY, "inferenceConfig": {"maxTokens": 16000}}
    stubber.add_response("converse", converse(
        [{"toolUse": {"toolUseId": "tooluse_1", "name": "crm_search_clients", "input": {"query": "Lyon"}}}],
        "tool_use"), first)
    stubber.add_response("converse", converse(
        [{"text": "À Lyon : Aciéries du Rhône (C-1001, client) et Clinique du Parc (C-1004, prospect)."}],
        "end_turn"), first)
    lines = []

    async with Client(server.mcp) as mcp_client:
        stop = await bedrock_mcp_client.ask(bedrock_mcp_client.QUESTION, mcp_client, bedrock, MODEL_ID, out=lines.append)

    stubber.assert_no_pending_responses()
    assert stop == "end_turn"
    assert lines == [
        S["call"],
        S["result_ok"],
        "À Lyon : Aciéries du Rhône (C-1001, client) et Clinique du Parc (C-1004, prospect).",
        S["stop"],
    ]


@pytest.mark.anyio
async def test_tools_offered_and_results_sent_back(crm_file):
    calls = []

    class Recorder:
        def converse(self, **kwargs):
            calls.append(copy.deepcopy(kwargs))  # the loop keeps appending to the same list
            if len(calls) == 1:
                return converse([{"toolUse": {"toolUseId": "t1", "name": "crm_search_clients",
                                              "input": {"query": "", "limit": 99}}}], "tool_use")
            return converse([{"text": "Je corrige la limite."}], "end_turn")

    async with Client(server.mcp) as mcp_client:
        await bedrock_mcp_client.ask("Tous les clients ?", mcp_client, Recorder(), MODEL_ID, out=lambda _: None)

    tools = calls[0]["toolConfig"]["tools"]
    assert [t["toolSpec"]["name"] for t in tools] == ["crm_search_clients"]  # crm_add_note is never offered
    assert tools[0]["toolSpec"]["inputSchema"]["json"]["properties"]["limit"]["maximum"] == 20
    tool_result = calls[1]["messages"][-1]["content"][0]["toolResult"]
    assert tool_result["toolUseId"] == "t1"
    assert tool_result["status"] == "error"  # the validation error goes back to the model
    assert "less than or equal to 20" in tool_result["content"][0]["text"]


@pytest.mark.anyio
async def test_disabled_tool_is_refused_without_running(crm_file):
    before = crm_file.read_text(encoding="utf-8")
    replies = iter([
        converse([{"toolUse": {"toolUseId": "t1", "name": "crm_add_note",
                               "input": {"client_id": "C-1002", "texte": "x", "auteur": "Léa"}}}], "tool_use"),
        converse([{"text": "Je ne peux pas écrire."}], "end_turn"),
    ])

    class Fake:
        def converse(self, **kwargs):
            return next(replies)

    lines = []
    async with Client(server.mcp) as mcp_client:
        await bedrock_mcp_client.ask("Ajoute une note", mcp_client, Fake(), MODEL_ID, out=lines.append)

    assert S["result_error"] in lines
    assert crm_file.read_text(encoding="utf-8") == before


def test_missing_model_id_exits_2(capsys):
    assert bedrock_mcp_client.main() == 2
    assert "BEDROCK_MODEL_ID" in capsys.readouterr().err


def test_provider_switch_in_appel_connecteur(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "bedrock")
    monkeypatch.setattr(bedrock_mcp_client, "main", lambda: 0)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(TARGET / "appel_connecteur.py"), run_name="__main__")
    assert exit_info.value.code == 0


def test_stdio_parameters_point_at_the_server(monkeypatch, crm_file):
    params = bedrock_mcp_client.server_parameters()
    assert params.args == [str(TARGET.resolve() / "server.py")]
    assert params.env == {"CRM_DATA": str(crm_file)}
