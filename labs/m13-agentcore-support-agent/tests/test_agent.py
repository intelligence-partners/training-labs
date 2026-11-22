"""The agent's logic with a scripted fake model and local stand-ins for the Gateway tools."""

import json

import pytest
from bedrock_agentcore.runtime import RequestContext
from starlette.testclient import TestClient

from fakes import FakeGateway, FakeModel

SESSION = "support-lab-session-0001-abcdefghijk"


@pytest.fixture
def agent(load_agent):
    main = load_agent()
    assert main.GATEWAY is None  # no AGENTCORE_GATEWAY_TOOLS_URL in the tests
    main._agents.clear()
    return main


def wire(main, monkeypatch, turns):
    model = FakeModel(turns)
    gateway = FakeGateway()
    monkeypatch.setattr(main, "MODEL", model)
    monkeypatch.setattr(main, "GATEWAY", gateway)
    return model, gateway


def call(main, payload, session_id=SESSION):
    return main.invoke(payload, RequestContext(session_id=session_id))


def tool_results(model_call):
    return [block["toolResult"] for message in model_call["messages"] for block in message["content"] if "toolResult" in block]


def test_defaults_match_the_lesson(agent):
    assert agent.MODEL_ID == "eu.anthropic.claude-opus-5-5"
    assert agent.MODEL.config["model_id"] == "eu.anthropic.claude-opus-5-5"
    assert "jamais plus" not in agent.SYSTEM_PROMPT  # the refund cap lives in Policy, not in the prompt
    assert "propose d'ouvrir un ticket" in agent.SYSTEM_PROMPT


def test_model_is_swappable_through_the_environment(load_agent):
    main = load_agent(MODEL_ID="eu.example.other-model-v1:0")
    assert main.MODEL.config["model_id"] == "eu.example.other-model-v1:0"


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"actorId": "c-4821"}, "prompt"),
        ({"prompt": "   ", "actorId": "c-4821"}, "prompt"),
        ({"prompt": 42, "actorId": "c-4821"}, "prompt"),
        ({"prompt": "Bonjour"}, "actorId"),
        ({"prompt": "Bonjour", "actorId": "c4"}, "actorId"),
        ({"prompt": "Bonjour", "actorId": "c-4821/../c-9999"}, "actorId"),
        ({"prompt": "Bonjour", "actorId": 4821}, "actorId"),
    ],
)
def test_invalid_payloads_are_rejected_before_the_model(agent, monkeypatch, payload, message):
    model, _ = wire(agent, monkeypatch, [])
    result = call(agent, payload)
    assert message in result["error"]
    assert model.calls == []


def test_order_status_reads_the_order_with_the_tool(agent, monkeypatch):
    answer = "Votre commande A-1042 a été expédiée avec Colissimo."
    model, gateway = wire(agent, monkeypatch, [{"tool": ("support___getOrder", {"orderId": "A-1042"})}, {"text": answer}])

    result = call(agent, {"prompt": "Bonjour, où en est ma commande A-1042 ?", "actorId": "c-4821"})

    assert result == {"result": answer}
    assert gateway.calls == [("getOrder", {"orderId": "A-1042"})]
    assert model.calls[0]["system_prompt"] == agent.SYSTEM_PROMPT
    assert model.calls[0]["tools"] == ["support___createRefund", "support___createTicket", "support___getOrder"]
    (first_result,) = tool_results(model.calls[1])
    assert first_result["status"] == "success"
    assert "expédiée" in first_result["content"][0]["text"]


def test_a_refused_refund_is_a_tool_result_the_agent_explains(agent, monkeypatch):
    explanation = "Je ne peux pas rembourser 120 euros. Je vous propose d'ouvrir un ticket."
    model, gateway = wire(
        agent,
        monkeypatch,
        [
            {"tool": ("support___createRefund", {"orderId": "A-1042", "amountCents": 12000, "reason": "colis endommagé"})},
            {"tool": ("support___createTicket", {"orderId": "A-1042", "summary": "Colis abîmé, remboursement de 120 euros refusé"})},
            {"text": explanation},
        ],
    )

    result = call(agent, {"prompt": "Je confirme, 120 euros.", "actorId": "c-4821"})

    assert result == {"result": explanation}
    assert [name for name, _ in gateway.calls] == ["createRefund", "createTicket"]
    refusal = tool_results(model.calls[1])[-1]
    assert refusal["status"] == "error"
    assert "Tool Execution Denied" in json.dumps(refusal)


def test_one_agent_per_session_and_actor(agent, monkeypatch):
    wire(agent, monkeypatch, [{"text": "un"}, {"text": "deux"}, {"text": "trois"}])
    call(agent, {"prompt": "Bonjour", "actorId": "c-4821"})
    first = agent._agents[(SESSION, "c-4821")]
    call(agent, {"prompt": "Encore", "actorId": "c-4821"})
    assert agent._agents[(SESSION, "c-4821")] is first
    call(agent, {"prompt": "Bonjour", "actorId": "c-9999"})
    assert set(agent._agents) == {(SESSION, "c-4821"), (SESSION, "c-9999")}
    assert agent._agents[(SESSION, "c-9999")] is not first


def test_missing_session_id_falls_back_to_a_local_session(agent, monkeypatch):
    wire(agent, monkeypatch, [{"text": "ok"}])
    call(agent, {"prompt": "Bonjour", "actorId": "c-4821"}, session_id=None)
    assert list(agent._agents) == [("local-dev-session-000000000000000000", "c-4821")]
    assert len("local-dev-session-000000000000000000") >= 33


def test_no_memory_configured_means_no_session_manager(agent, monkeypatch):
    wire(agent, monkeypatch, [{"text": "ok"}])
    call(agent, {"prompt": "Bonjour", "actorId": "c-4821"})
    assert agent._agents[(SESSION, "c-4821")]._session_manager is None


def test_the_runtime_http_contract(agent, monkeypatch):
    """POST /invocations as AgentCore Runtime calls the container, through the real SDK app."""
    answer = "Votre commande A-1042 a été expédiée avec Colissimo."
    wire(agent, monkeypatch, [{"tool": ("support___getOrder", {"orderId": "A-1042"})}, {"text": answer}])
    client = TestClient(agent.app)

    assert client.get("/ping").status_code == 200
    response = client.post(
        "/invocations",
        json={"prompt": "Bonjour, où en est ma commande A-1042 ?", "actorId": "c-4821"},
        headers={"X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": SESSION},
    )
    assert response.status_code == 200
    assert response.json() == {"result": answer}
    assert (SESSION, "c-4821") in agent._agents
