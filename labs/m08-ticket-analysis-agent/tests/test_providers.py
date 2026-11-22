"""Optional provider switch: MODEL_PROVIDER, the Converse translation and a full run on Converse.

Converse calls go through a real boto3 ``bedrock-runtime`` client with botocore's Stubber, so
every request is validated against the Converse service model; nothing leaves the machine.
"""
import json
import sys

import boto3
import pytest
from botocore.stub import Stubber

import agent
import providers
from providers import ConverseBlock, ConverseClient, to_converse_request


def converse_response(content, stop_reason="end_turn", input_tokens=1000, output_tokens=100, cache_read=0,
                      cache_write=0):
    usage = {"inputTokens": input_tokens, "outputTokens": output_tokens,
             "totalTokens": input_tokens + output_tokens + cache_read + cache_write,
             "cacheReadInputTokens": cache_read, "cacheWriteInputTokens": cache_write}
    return {"output": {"message": {"role": "assistant", "content": content}}, "stopReason": stop_reason,
            "usage": usage, "metrics": {"latencyMs": 120}}


@pytest.fixture
def runtime():
    """A stubbed bedrock-runtime client; ``runtime.sent`` records the validated Converse params."""
    client = boto3.client("bedrock-runtime", region_name="eu-west-3")
    stubber = Stubber(client)
    client.sent = []
    client.meta.events.register("provide-client-params.bedrock-runtime.Converse",
                                lambda params, **_: client.sent.append(json.loads(json.dumps(params))))
    stubber.activate()
    client.stubber = stubber
    yield client
    stubber.deactivate()


def test_provider_selection(monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    assert providers.current_provider() == "anthropic"
    assert providers.model_for("claude-opus-5-5") == "claude-opus-5-5"
    monkeypatch.setenv("MODEL_PROVIDER", "bedrock")
    with pytest.raises(SystemExit, match="BEDROCK_MODEL_ID"):
        providers.model_for("claude-opus-5-5")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "my-profile-id")
    assert providers.model_for("claude-opus-5-5") == "my-profile-id"
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    with pytest.raises(SystemExit, match="not supported"):
        providers.current_provider()


def test_make_client_per_provider(monkeypatch):
    import anthropic

    monkeypatch.setenv("AWS_REGION", "eu-west-3")
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    assert isinstance(providers.make_client(), anthropic.Anthropic)
    monkeypatch.setenv("MODEL_PROVIDER", "anthropic-bedrock")
    assert isinstance(providers.make_client(), anthropic.AnthropicBedrock)
    monkeypatch.setenv("MODEL_PROVIDER", "bedrock")
    client = providers.make_client()
    assert isinstance(client, ConverseClient) and client.runtime.meta.region_name == "eu-west-3"


def test_price_sheet_override(monkeypatch, capsys):
    default = {"input": 4.0, "output": 20.0, "cache_write": 5.0, "cache_read": 0.2}
    assert providers.prices_from_env(default) == default
    monkeypatch.setenv("PRICE_SHEET", '{"input": 1, "output": 2, "cache_write": 0, "cache_read": 0}')
    assert providers.prices_from_env(default) == {"input": 1.0, "output": 2.0, "cache_write": 0.0, "cache_read": 0.0}
    monkeypatch.setenv("PRICE_SHEET", '{"input": 1}')
    with pytest.raises(SystemExit, match="output, cache_write, cache_read"):
        providers.prices_from_env(default)
    monkeypatch.delenv("PRICE_SHEET")
    monkeypatch.setenv("MODEL_PROVIDER", "bedrock")
    providers.prices_from_env(default)
    assert "PRICE_SHEET is not set" in capsys.readouterr().err


def test_translation_of_the_lab_request(monkeypatch):
    request = to_converse_request(
        model="m", max_tokens=16000, system=agent.SYSTEM, output_config={"effort": "medium"},
        cache_control={"type": "ephemeral"}, tools=agent.TOOLS, thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": "Traite les tickets ouverts."}])
    assert request["system"] == [{"text": agent.SYSTEM}]
    assert request["inferenceConfig"] == {"maxTokens": 16000}
    assert request["messages"] == [{"role": "user", "content": [{"text": "Traite les tickets ouverts."},
                                                                {"cachePoint": {"type": "default"}}]}]
    first = request["toolConfig"]["tools"][0]["toolSpec"]
    assert first["name"] == "list_tickets" and first["strict"] is True
    assert first["inputSchema"]["json"] == agent.TOOLS[0]["input_schema"]
    assert "outputConfig" not in request  # effort is Claude-specific: not sent

    monkeypatch.setenv("BEDROCK_CACHE_POINTS", "false")
    monkeypatch.setenv("BEDROCK_STRICT_TOOLS", "false")
    monkeypatch.setenv("BEDROCK_MAX_TOKENS", "4096")
    request = to_converse_request(model="m", max_tokens=16000, cache_control={"type": "ephemeral"},
                                  tools=agent.TOOLS, messages=[{"role": "user", "content": "x"}])
    assert request["messages"][0]["content"] == [{"text": "x"}]
    assert "strict" not in request["toolConfig"]["tools"][0]["toolSpec"]
    assert request["inferenceConfig"] == {"maxTokens": 4096}


def test_translation_of_tool_results_structured_output_and_cache_markers():
    request = to_converse_request(
        model="m", max_tokens=512,
        system=[{"type": "text", "text": "policy", "cache_control": {"type": "ephemeral"}}],
        output_config={"format": {"type": "json_schema", "schema": {"type": "object"}}},
        messages=[
            {"role": "user", "content": "go"},
            {"role": "assistant", "content": [{"type": "text", "text": " "},
                                              {"type": "tool_use", "id": "t1", "name": "lire", "input": {}}]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "{}"}]},
                {"type": "tool_result", "tool_use_id": "t2", "content": "nope", "is_error": True},
                {"type": "text", "text": "wrap up"}]},
        ])
    assert request["system"] == [{"text": "policy"}, {"cachePoint": {"type": "default"}}]
    assert request["messages"][1]["content"] == [{"toolUse": {"toolUseId": "t1", "name": "lire", "input": {}}}]
    assert request["messages"][2]["content"] == [
        {"toolResult": {"toolUseId": "t1", "content": [{"text": "{}"}]}},
        {"toolResult": {"toolUseId": "t2", "content": [{"text": "nope"}], "status": "error"}},
        {"text": "wrap up"}]
    fmt = request["outputConfig"]["textFormat"]
    assert fmt["type"] == "json_schema" and json.loads(fmt["structure"]["jsonSchema"]["schema"]) == {"type": "object"}
    with pytest.raises(TypeError):
        to_converse_request(model="m", max_tokens=1, messages=[], tool_choice={"type": "auto"})


def test_response_blocks_are_replayed_unchanged(runtime):
    reasoning = {"reasoningContent": {"reasoningText": {"text": "...", "signature": "sig"}}}
    runtime.stubber.add_response("converse", converse_response(
        [reasoning, {"toolUse": {"toolUseId": "tu1", "name": "search_kb", "input": {"query": "sso"}}}], "tool_use",
        cache_read=50, cache_write=20))
    runtime.stubber.add_response("converse", converse_response([{"text": "fin"}]))
    client = ConverseClient(runtime)
    first = client.messages.create(model="m", max_tokens=100, messages=[{"role": "user", "content": "q"}],
                                   tools=agent.TOOLS)
    assert [b.type for b in first.content] == ["thinking", "tool_use"]
    assert first.stop_reason == "tool_use"
    assert (first.usage.input_tokens, first.usage.cache_read_input_tokens,
            first.usage.cache_creation_input_tokens) == (1000, 50, 20)
    with client.messages.stream(model="m", max_tokens=100, tools=agent.TOOLS, messages=[
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": first.content},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu1", "content": "[]"}]},
    ]) as stream:
        final = stream.get_final_message()
    assert final.content[0].text == "fin"
    assert runtime.sent[1]["messages"][1]["content"][0] == reasoning
    runtime.stubber.assert_no_pending_responses()


def test_full_agent_run_on_converse(lab_dir, runtime, monkeypatch, capsys):
    runtime.stubber.add_response("converse", converse_response(
        [{"text": "Je commence."}, {"toolUse": {"toolUseId": "tu1", "name": "get_ticket",
                                                 "input": {"ticket_id": "T-12"}}}], "tool_use"))
    runtime.stubber.add_response("converse", converse_response(
        [{"toolUse": {"toolUseId": "tu2", "name": "escalate",
                      "input": {"ticket_id": "T-1005", "team": "juridique", "summary": "x"}}}], "tool_use"))
    runtime.stubber.add_response("converse", converse_response([{"text": "Rapport"}]))
    monkeypatch.setattr(agent, "make_client", lambda: ConverseClient(runtime))
    monkeypatch.setattr(agent, "MODEL", "eu.example-model-id")
    monkeypatch.setattr(sys, "argv", ["agent.py", "--auto-refus", "Traite les tickets ouverts."])
    assert agent.main() == 0
    assert "Tours : 3 | Coût estimé : 0.02 $ | Rapport : rapport.md" in capsys.readouterr().out
    second = runtime.sent[1]
    assert second["modelId"] == "eu.example-model-id"
    results = second["messages"][2]["content"]
    assert results[0]["toolResult"]["status"] == "error"
    assert results[0]["toolResult"]["content"] == [{"text": "Identifiant invalide : T-12. Format attendu : T-1234."}]
    assert results[-1] == {"cachePoint": {"type": "default"}}
    third = runtime.sent[2]["messages"][-1]["content"][0]["toolResult"]
    assert third["status"] == "error" and third["content"][0]["text"].startswith("Action refusée")
    runtime.stubber.assert_no_pending_responses()
