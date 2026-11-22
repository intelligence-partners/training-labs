"""Steps 5, 6, 7 and 11: the instrumented agent, its cost, its quality score and its metrics."""
import re

import pytest

import agent
from conftest import stubbed
from fake_anthropic import FakeClaude, message, text, tool_use
from providers import ConverseClient

PUBLISHED = ["TacheTerminee", "TacheReussie", "CoutTacheUSD", "DureeTacheMs", "ToursParTache",
             "TokensEntreeTotal", "TokensLusEnCache"]


def triage(categorie, priorite, **usage):
    return message([tool_use("enregistrer_tri", {"categorie": categorie, "priorite": priorite,
                                                  "justification": "politique"})], "tool_use", **usage)


@pytest.fixture
def claude(monkeypatch):
    fake = FakeClaude()
    monkeypatch.setattr(agent, "client", fake.client)
    return fake


def test_t05_trace_cost_and_score(claude, spans):
    claude.add(
        message([tool_use("chercher_client", {"email": "compta@menuiserie-roux.fr"})], "tool_use",
                input_tokens=50, cache_write=6000, output_tokens=80),
        message([tool_use("consulter_commande", {"numero": "CMD-5521"})], "tool_use",
                input_tokens=60, cache_read=6100, output_tokens=70),
        triage("livraison", "P2", input_tokens=70, cache_read=6200, output_tokens=90),
    )
    r = agent.traiter(agent.TICKETS[4])
    assert r["id"] == "T05" and r["reussie"] is True and r["tours"] == 3
    expected = (180 * 4.00 + 6000 * 5.00 + 12300 * 0.20 + 240 * 20.00) / 1_000_000
    assert r["cout_usd"] == pytest.approx(expected)
    assert r["tokens_entree_total"] == 180 + 6000 + 12300 and r["tokens_lus_cache"] == 12300

    # Requests: streamed, the lesson's parameters, the cache breakpoint on the system prompt.
    first = claude.requests[0]
    assert first["stream"] is True
    assert first["model"] == "eu.anthropic.claude-opus-5-5" and first["max_tokens"] == 4096
    assert first["output_config"] == {"effort": "low"}
    assert first["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert [t["name"] for t in first["tools"]] == ["chercher_client", "consulter_commande", "enregistrer_tri"]
    assert claude.requests[1]["messages"][-1]["content"][0]["content"] == (
        '{"id": "C-207", "segment": "PME", "activite": "normale"}')

    # Trace: invoke_agent > (anthropic.messages.create, execute_tool) x 3, as in the step 7 exercise.
    finished = spans.get_finished_spans()
    root = next(s for s in finished if s.name == "invoke_agent agent-support")
    children = sorted((s for s in finished if s.parent and s.parent.span_id == root.context.span_id),
                      key=lambda s: s.start_time)
    assert [s.name for s in children] == [
        "anthropic.messages.create", "execute_tool chercher_client",
        "anthropic.messages.create", "execute_tool consulter_commande",
        "anthropic.messages.create", "execute_tool enregistrer_tri"]
    attributes = dict(root.attributes)
    assert attributes["app.task.id"] == "T05" and attributes["app.prompt.version"] == "v1"
    assert attributes["app.task.turns"] == 3 and attributes["app.task.outcome"] == "reussie"
    assert attributes["app.task.cost_usd"] == round(expected, 6)
    assert attributes["app.task.stop_reason"] == "tool_use"
    assert attributes["gen_ai.operation.name"] == "invoke_agent"
    tool_span = children[1]
    assert tool_span.attributes["gen_ai.tool.name"] == "chercher_client"


@pytest.mark.parametrize("responses, outcome", [
    ([message([text("Je ne sais pas.")])], "end_turn"),
    ([message([text("")], "refusal")], "refusal"),
    ([triage("livraison", "P3")], "tool_use"),  # wrong priority for T05
])
def test_failed_tasks(claude, spans, responses, outcome):
    claude.add(*responses)
    r = agent.traiter(agent.TICKETS[4])
    assert r["reussie"] is False
    root = next(s for s in spans.get_finished_spans() if s.name == "invoke_agent agent-support")
    assert root.attributes["app.task.outcome"] == "echec"
    assert root.attributes["app.task.stop_reason"] == outcome


def test_turn_limit(claude):
    claude.add(*[message([tool_use("chercher_client", {"email": "x@y.z"})], "tool_use")] * agent.MAX_TOURS)
    r = agent.traiter(agent.TICKETS[0])
    assert r["tours"] == agent.MAX_TOURS == 6 and r["reussie"] is False
    assert claude.requests[1]["messages"][-1]["content"][0]["content"] == '{"erreur": "client inconnu"}'


def test_score_requires_the_tool_when_expected():
    ticket = agent.TICKETS[0]  # T01 requires consulter_commande
    good = {"categorie": "livraison", "priorite": "P1"}
    assert agent.noter(ticket, good, ["chercher_client", "consulter_commande", "enregistrer_tri"])
    assert not agent.noter(ticket, good, ["chercher_client", "enregistrer_tri"])
    assert not agent.noter(ticket, None, [])


def test_prompt_v1_is_stable_and_v2_breaks_the_prefix():
    v1 = agent.systeme("v1")
    assert v1 == agent.systeme("v1")
    assert v1[0]["cache_control"] == {"type": "ephemeral"}
    assert v1[0]["text"].count("REF-") == 300
    first, second = agent.systeme("v2")[0]["text"], agent.systeme("v2")[0]["text"]
    assert first != second and first.startswith("Horodatage de la requête : ")
    assert first.split("\n\n", 1)[1] == v1[0]["text"]


def test_publier_sends_each_metric_with_and_without_prompt_version(cloudwatch):
    cloudwatch.stubber.add_response("put_metric_data", {})
    agent.publier({"id": "T01", "reussie": True, "tours": 3, "cout_usd": 0.0312, "duree_ms": 9400.0,
                   "tokens_entree_total": 7000, "tokens_lus_cache": 6100})
    sent = cloudwatch.sent[0]
    assert sent["Namespace"] == "M14/AgentSupport"
    data = sent["MetricData"]
    assert [d["MetricName"] for d in data[::2]] == PUBLISHED
    assert all("Dimensions" not in d for d in data[::2])
    assert all(d["Dimensions"] == [{"Name": "PromptVersion", "Value": "v1"}] for d in data[1::2])
    assert data[4]["Value"] == 0.0312 and data[4]["Unit"] == "None"
    cloudwatch.stubber.assert_no_pending_responses()


def test_main_prints_the_lines_checked_by_the_lesson(claude, cloudwatch, capsys):
    for ticket in agent.TICKETS:
        expected = ticket["attendu"]
        if "outil_requis" in expected:
            claude.add(message([tool_use("consulter_commande", {"numero": "CMD-5702"})], "tool_use",
                               input_tokens=40, cache_read=6000, output_tokens=50))
        claude.add(triage(expected["categorie"], expected["priorite"], input_tokens=40, cache_read=6000,
                          output_tokens=60))
        cloudwatch.stubber.add_response("put_metric_data", {})
    agent.main()
    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    assert len(lines) == 9
    assert re.match(r"\[v1\] T01 ok    tours=2 coût=\d+\.\d{4} \$ durée=\d+\.\d s cache=\d+%", lines[0])
    summary = lines[-1]
    assert re.search(r"Synthèse v1 : réussite [5-8]/8", summary)
    assert re.search(r"coût par tâche réussie \d+\.\d{4} \$", summary)
    assert re.search(r"lecture cache ([5-9]\d|100) ?%", summary)
    assert "réussite 8/8" in summary and "lecture cache 99%" in summary
    cloudwatch.stubber.assert_no_pending_responses()


def test_cache_rate_exercise():
    assert round(100 * 186_000 / 205_000, 1) == 90.7


def test_same_agent_on_converse(monkeypatch, spans):
    """MODEL_PROVIDER=bedrock: the boto3 Converse API, for another Bedrock model family."""
    runtime = stubbed("bedrock-runtime")
    usage = {"inputTokens": 50, "outputTokens": 40, "totalTokens": 6090, "cacheReadInputTokens": 6000,
             "cacheWriteInputTokens": 0}
    runtime.stubber.add_response("converse", {
        "output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": "tu1", "name": "chercher_client",
                         "input": {"email": "contact@cabinet-lefort.fr"}}}]}},
        "stopReason": "tool_use", "usage": usage, "metrics": {"latencyMs": 300}})
    runtime.stubber.add_response("converse", {
        "output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": "tu2", "name": "enregistrer_tri",
                         "input": {"categorie": "compte", "priorite": "P3", "justification": "TPE"}}}]}},
        "stopReason": "tool_use", "usage": usage, "metrics": {"latencyMs": 300}})
    monkeypatch.setattr(agent, "client", ConverseClient(runtime))
    monkeypatch.setattr(agent, "MODELE", "eu.example-other-model")
    r = agent.traiter(agent.TICKETS[3])  # T04
    assert r["reussie"] is True and r["tours"] == 2 and r["tokens_lus_cache"] == 12000
    request = runtime.sent[0]
    assert request["modelId"] == "eu.example-other-model"
    assert request["system"][-1] == {"cachePoint": {"type": "default"}}
    assert request["inferenceConfig"] == {"maxTokens": 4096}
    assert runtime.sent[1]["messages"][2]["content"][0]["toolResult"]["toolUseId"] == "tu1"
    runtime.stubber.assert_no_pending_responses()
