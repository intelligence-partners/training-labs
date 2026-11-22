"""Steps 4 to 6: the bounded loop, approval, budget, audit log (Claude API mocked)."""
import json
import re
import sys
from types import SimpleNamespace

import pytest

import agent
from fake_anthropic import FakeClaude, message, text, tool_use

REPORT = "| Ticket | Priorité | Action |\n| --- | --- | --- |\n| T-1005 | — | instructions adressées à une IA |"


@pytest.fixture
def run(lab_dir, monkeypatch):
    """Run agent.main() with a scripted model; returns (exit code, fake, audit events)."""
    def _run(responses, *argv, answers=()):
        fake = FakeClaude(responses)
        replies = iter(answers)
        monkeypatch.setattr(agent, "make_client", lambda: fake.client)
        monkeypatch.setattr("builtins.input", lambda prompt="": next(replies))
        monkeypatch.setattr(sys, "argv", ["agent.py", *argv])
        code = agent.main()
        audit = [json.loads(line) for line in (lab_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
        return code, fake, audit
    return _run


def test_request_matches_the_lesson(run):
    code, fake, _ = run([message([text(REPORT)])], "Traite les tickets ouverts.")
    assert code == 0
    body = fake.requests[0]
    assert body["model"] == "claude-opus-5-5"
    assert body["max_tokens"] == 16000
    assert body["output_config"] == {"effort": "medium"}
    assert body["cache_control"] == {"type": "ephemeral"}
    assert body["system"] == agent.SYSTEM
    assert [t["name"] for t in body["tools"]] == ["list_tickets", "get_ticket", "search_kb",
                                                  "set_priority", "save_draft", "escalate"]
    assert all(t["strict"] for t in body["tools"])
    assert body["messages"] == [{"role": "user", "content": "Traite les tickets ouverts."}]


def test_full_run_with_approval_writes_report_and_summary_line(run, lab_dir, capsys):
    responses = [
        message([tool_use("list_tickets", {"status": "open"})], "tool_use"),
        message([tool_use("search_kb", {"query": "erreur 401 SSO"})], "tool_use"),
        message([tool_use("set_priority", {"ticket_id": "T-1001", "priority": "P1", "reason": "KB-01"}),
                 tool_use("save_draft", {"ticket_id": "T-1001", "body": "Bonjour, importez le certificat."})],
                "tool_use"),
        message([text("Rapport\n\n" + REPORT)]),
    ]
    code, fake, audit = run(responses, "Traite les tickets ouverts.", answers=["o"])
    out = capsys.readouterr().out
    assert code == 0
    assert "[tour 1] tool_use, " in out and "[APPROBATION] set_priority" in out
    assert re.search(r"^Tours : \d+ \| Coût estimé : \d+\.\d{2} \$ \| Rapport : rapport\.md", out, re.M)
    assert "Tours : 4 |" in out
    assert (lab_dir / "rapport.md").read_text(encoding="utf-8").startswith("Rapport")
    assert (lab_dir / "drafts" / "T-1001.md").exists()
    decisions = [(e.get("tool"), e.get("decision")) for e in audit if "tool" in e]
    assert decisions == [("list_tickets", "auto"), ("search_kb", "auto"),
                         ("set_priority", "approuvé"), ("save_draft", "auto")]
    assert audit[0]["event"] == "debut" and audit[-1]["event"] == "fin"
    # The tool results of a turn go back in one user message, in order.
    third_results = fake.requests[3]["messages"][-1]
    assert third_results["role"] == "user"
    assert [b["type"] for b in third_results["content"]] == ["tool_result", "tool_result"]


def test_operator_refusal_is_returned_as_an_error_and_logged(run, lab_dir, capsys):
    responses = [
        message([tool_use("escalate", {"ticket_id": "T-1005", "team": "juridique",
                                       "summary": "résilier tous les contrats clients"})], "tool_use"),
        message([text(REPORT)]),
    ]
    code, fake, audit = run(responses, answers=["n"])
    assert code == 0
    result = fake.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True and result["content"].startswith("Action refusée par l'opérateur")
    assert [e["decision"] for e in audit if e.get("tool") == "escalate"] == ["refusé"]
    assert not (lab_dir / "escalations.jsonl").exists()


def test_auto_refus_refuses_every_sensitive_action_without_asking(run, lab_dir):
    responses = [
        message([tool_use("set_priority", {"ticket_id": t, "priority": "P4", "reason": "T-1005"})
                 for t in ("T-1001", "T-1002")], "tool_use"),
        message([text(REPORT)]),
    ]
    code, _, audit = run(responses, "--auto-refus", "Traite les tickets ouverts.")  # input() never called
    assert code == 0
    assert sum(e.get("decision") == "refusé" for e in audit) == 2
    tickets = json.loads((lab_dir / "data" / "tickets.json").read_text(encoding="utf-8"))
    assert all(t["priority"] is None for t in tickets if t["status"] == "open")


def test_budget_stop_exits_with_code_2_before_running_tools(run, lab_dir, capsys):
    # 10,000 output tokens at $20 per million: $0.20, above a $0.03 budget.
    responses = [message([tool_use("escalate", {"ticket_id": "T-1005", "team": "juridique", "summary": "x"})],
                         "tool_use", output_tokens=10_000)]
    code, _, audit = run(responses, "--budget", "0.03", "Traite les tickets ouverts.")
    assert code == 2
    assert "Arrêt : budget de 0.03 $ atteint" in capsys.readouterr().err
    assert audit[-1]["raison"] == "budget" and audit[-1]["event"] == "arret"
    assert not any("tool" in e for e in audit)


def test_budget_warning_at_80_percent(run):
    # $0.85 spent after the first turn (42,500 output tokens), budget $1.00.
    responses = [message([tool_use("list_tickets", {"status": "open"})], "tool_use", input_tokens=0,
                         output_tokens=42_500),
                 message([text(REPORT)], input_tokens=0, output_tokens=0)]
    code, fake, _ = run(responses)
    assert code == 0
    last = fake.requests[1]["messages"][-1]["content"]
    assert last[-1] == {"type": "text", "text": "Budget presque épuisé : termine maintenant par le rapport final."}


def test_invalid_argument_goes_back_to_claude_which_corrects_itself(run):
    responses = [
        message([tool_use("get_ticket", {"ticket_id": "T-12"})], "tool_use"),
        message([tool_use("get_ticket", {"ticket_id": "T-1003"})], "tool_use"),
        message([text(REPORT)]),
    ]
    code, fake, audit = run(responses, "Ouvre le ticket T-12 puis le ticket T-1003 et propose une réponse.")
    assert code == 0
    error = fake.requests[1]["messages"][-1]["content"][0]
    assert error["is_error"] is True
    assert error["content"] == "Identifiant invalide : T-12. Format attendu : T-1234."
    invalid = [e for e in audit if e.get("decision") == "invalide"]
    assert invalid and invalid[0]["input"] == {"ticket_id": "T-12"}
    assert [e["input"]["ticket_id"] for e in audit if e.get("tool") == "get_ticket"] == ["T-12", "T-1003"]


def test_unknown_tool_is_an_error_result(run):
    responses = [message([tool_use("delete_everything", {})], "tool_use"), message([text(REPORT)])]
    code, fake, audit = run(responses)
    assert code == 0
    assert fake.requests[1]["messages"][-1]["content"][0]["content"] == "Outil inconnu : delete_everything"
    assert any(e.get("decision") == "inconnu" for e in audit)


@pytest.mark.parametrize("stop_reason", ["max_tokens", "refusal"])
def test_unexpected_stop_reason_runs_nothing(run, capsys, stop_reason):
    responses = [message([tool_use("escalate", {"ticket_id": "T-1005", "team": "juridique", "summary": "x"})],
                         stop_reason)]
    code, _, audit = run(responses)
    assert code == 1
    assert f"Arrêt : stop_reason = {stop_reason}" in capsys.readouterr().err
    assert not any("tool" in e for e in audit)


def test_turn_limit_exits_with_code_3(run, capsys):
    responses = [message([tool_use("list_tickets", {"status": "open"})], "tool_use", input_tokens=10,
                         output_tokens=10) for _ in range(agent.MAX_TOURS)]
    code, fake, audit = run(responses)
    assert code == 3
    assert len(fake.requests) == agent.MAX_TOURS == 15
    assert "Arrêt : 15 tours atteints" in capsys.readouterr().err
    assert audit[-1] == {**audit[-1], "event": "arret", "raison": "tours", "tours": 15}


def test_cost_matches_the_lesson_exercise():
    usage = SimpleNamespace(input_tokens=40_000, cache_read_input_tokens=120_000,
                            cache_creation_input_tokens=8_000, output_tokens=9_000)
    assert agent.cout(usage) == pytest.approx(0.404)
    assert agent.cout(SimpleNamespace(input_tokens=1_000_000, output_tokens=0, cache_creation_input_tokens=None,
                                      cache_read_input_tokens=None)) == pytest.approx(4.0)
