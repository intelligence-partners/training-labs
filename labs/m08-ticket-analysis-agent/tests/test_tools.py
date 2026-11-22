"""Step 3: the six tools, their schemas and their business validation (no model call)."""
import json
import subprocess
import sys

import pytest

import tools
from tools import ToolInputError


def test_lesson_commands_print_the_expected_output(code_copy):
    """The three commands of step 3, run as written in the lesson."""
    run = lambda code: subprocess.run([sys.executable, "-c", code], cwd=code_copy,  # noqa: E731
                                      capture_output=True, text=True, timeout=60)

    first = run("import json, tools; print(json.dumps(tools.list_tickets('open'), ensure_ascii=False)[:70])")
    assert first.returncode == 0, first.stderr
    assert first.stdout.startswith('{"count": 5, "tickets": [{"id": "T-1001"')

    second = run("import tools; print([r['id'] for r in tools.search_kb('erreur 401 SSO')['results']])")
    assert second.stdout.strip() == "['KB-01']"

    third = run("import tools; tools.get_ticket('T-12')")
    assert third.returncode != 0
    assert third.stderr.strip().endswith("ToolInputError: Identifiant invalide : T-12. Format attendu : T-1234.")


def test_list_tickets_returns_only_triage_fields(lab_dir):
    result = tools.list_tickets("open")
    assert result["count"] == 5
    assert [t["id"] for t in result["tickets"]] == ["T-1001", "T-1002", "T-1003", "T-1004", "T-1005"]
    assert set(result["tickets"][0]) == {"id", "subject", "customer", "created_at", "priority"}
    assert tools.list_tickets("closed")["tickets"][0]["id"] == "T-0999"


def test_get_ticket_tags_the_body_as_untrusted_data(lab_dir):
    ticket = tools.get_ticket("T-1005")
    assert ticket["body"].startswith("<contenu_client>\n")
    assert ticket["body"].endswith("\n</contenu_client>")
    assert ticket["customer"] == "Société Nouvelle Horizon"


@pytest.mark.parametrize("ticket_id, message", [
    ("T-12", "Identifiant invalide : T-12. Format attendu : T-1234."),
    ("../etc/passwd", "Identifiant invalide : ../etc/passwd. Format attendu : T-1234."),
    ("T-4242", "Ticket T-4242 introuvable. Utilise list_tickets pour voir les identifiants."),
])
def test_invalid_or_unknown_ids_are_rejected(lab_dir, ticket_id, message):
    with pytest.raises(ToolInputError) as exc:
        tools.get_ticket(ticket_id)
    assert str(exc.value) == message


def test_search_kb_ranks_articles(lab_dir):
    assert [a["id"] for a in tools.search_kb("facture prélevée deux fois")["results"]][0] == "KB-02"
    assert tools.search_kb("xyz")["results"] == []


def test_set_priority_validates_then_writes(lab_dir):
    with pytest.raises(ToolInputError, match="Priorité inconnue : P0"):
        tools.set_priority("T-1001", "P0", "test")
    assert tools.set_priority("T-1001", "P1", "KB-01 : client bloqué") == {"ticket_id": "T-1001", "priority": "P1"}
    saved = json.loads((lab_dir / "data" / "tickets.json").read_text(encoding="utf-8"))
    assert saved[0]["priority"] == "P1" and saved[0]["priority_reason"] == "KB-01 : client bloqué"
    assert saved[1]["priority"] is None


def test_save_draft_builds_the_path_itself(lab_dir):
    assert tools.save_draft("T-1003", "Bonjour,\nvoici la marche à suivre.") == {"saved": "drafts/T-1003.md"}
    assert (lab_dir / "drafts" / "T-1003.md").read_text(encoding="utf-8").startswith("Bonjour")
    with pytest.raises(ToolInputError, match="Brouillon trop long"):
        tools.save_draft("T-1003", "x" * 4001)
    with pytest.raises(ToolInputError):
        tools.save_draft("../../x", "texte")


def test_escalate_validates_the_team_and_appends(lab_dir):
    with pytest.raises(ToolInputError, match="Équipe inconnue : direction"):
        tools.escalate("T-1002", "direction", "...")
    tools.escalate("T-1002", "facturation", "Double prélèvement F-2026-10-0412.")
    lines = (lab_dir / "escalations.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0]) == {"ticket_id": "T-1002", "team": "facturation",
                                    "summary": "Double prélèvement F-2026-10-0412."}


def test_tool_definitions_are_strict_and_match_the_handlers():
    assert [t["name"] for t in tools.TOOLS] == list(tools.HANDLERS)
    assert tools.SENSIBLES == {"set_priority", "escalate"}
    for tool in tools.TOOLS:
        schema = tool["input_schema"]
        assert tool["strict"] is True and tool["description"]
        assert schema["additionalProperties"] is False
        assert schema["required"] == list(schema["properties"])
    priority = next(t for t in tools.TOOLS if t["name"] == "set_priority")
    assert priority["input_schema"]["properties"]["priority"]["enum"] == ["P1", "P2", "P3", "P4"]
    escalate = next(t for t in tools.TOOLS if t["name"] == "escalate")
    assert escalate["input_schema"]["properties"]["team"]["enum"] == ["facturation", "technique", "juridique"]
