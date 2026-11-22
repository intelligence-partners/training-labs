"""Steps 3, 4, 8, 9, 10 and the cleanup: consistency of infra/ with the agent and the lesson.

`terraform fmt`, `terraform init -backend=false` and `terraform validate` run in test.sh; these
tests check what Terraform cannot: the dashboard JSON, the metric names shared by the agent,
the dashboard and the alarms, and the commands run by cleanup.sh (against fake CLIs).
"""
import json
import os
import re
import stat
import subprocess
from pathlib import Path

from conftest import LAB
from test_agent import PUBLISHED

INFRA = LAB / "infra"


def hcl() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(INFRA.glob("*.tf")))


def rendered_dashboard(region="eu-west-3", model="eu.anthropic.claude-opus-5-5") -> dict:
    body = (INFRA / "tableau.json.tftpl").read_text(encoding="utf-8")
    placeholders = set(re.findall(r"\$\{(\w+)\}", body))
    assert placeholders == {"region", "model_id_observe"}  # the variables passed by dashboard.tf
    return json.loads(body.replace("${region}", region).replace("${model_id_observe}", model))


def test_dashboard_matches_the_lesson_and_the_published_metrics():
    widgets = rendered_dashboard()["widgets"]
    assert [w["properties"]["title"] for w in widgets] == [
        "Taux de réussite (%)", "Coût moyen par tâche ($)", "Lecture du cache (%)",
        "Bedrock : TTFT et latence p95 (ms)", "Bedrock : limitations et erreurs"]
    for widget in widgets:
        props = widget["properties"]
        assert props["region"] == "eu-west-3"
        ids = {m[-1]["id"] for m in props["metrics"] if isinstance(m[-1], dict) and "id" in m[-1]}
        for metric in props["metrics"]:
            if isinstance(metric[0], dict):  # an expression: every id it uses must exist
                used = set(re.findall(r"[a-z]\w*", metric[0]["expression"]))
                assert used <= ids, (props["title"], used - ids)
            elif metric[0] == "M14/AgentSupport":
                assert metric[1] in PUBLISHED
            else:
                assert metric[0] == "AWS/Bedrock"
    bedrock = widgets[3]["properties"]["metrics"]
    assert bedrock[0] == ["AWS/Bedrock", "TimeToFirstToken", "ModelId", "eu.anthropic.claude-opus-5-5"]


def test_alarms_read_metrics_the_agent_publishes():
    text = hcl()
    names = re.findall(r'metric_name\s*=\s*"(\w+)"', text)
    assert names and set(names) <= set(PUBLISHED)
    assert re.findall(r'alarm_name\s*=\s*"([\w-]+)"', text) == [
        "m14-cout-moyen-tache", "m14-taux-reussite", "m14-taux-cache"]
    assert 'expression  = "100 * lus / tot"' in text and "threshold           = 50" in text
    assert text.count('treat_missing_data  = "notBreaching"') == 3


def test_resource_names_match_the_lesson():
    text = hcl()
    for name in ['"/m14/bedrock-invocations"', '"m14-bedrock-logs"', '"ecrire-journaux"',
                 '"m14-transaction-search"', '"m14-agent-support"', '"m14-alertes"', '"m14-lab"']:
        assert name in text, name
    assert re.search(r'version\s*=\s*"= \d+\.\d+\.\d+"', text), "the provider version must be pinned"
    assert "retention_in_days = 7" in text and "text_data_delivery_enabled      = true" in text


def _fake_cli(directory: Path, name: str, body: str) -> None:
    path = directory / name
    path.write_text(f"#!/usr/bin/env bash\necho \"{name} $*\" >> \"$CALLS\"\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def run_cleanup(tmp_path, transaction_search: str, previous: str | None = None):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _fake_cli(bin_dir, "terraform", f"""
case "$*" in
  *"output -raw region"*) printf eu-west-3 ;;
  *"output -raw transaction_search_managed_by_lab"*) printf {transaction_search} ;;
esac""")
    _fake_cli(bin_dir, "aws", "")
    lab = tmp_path / "lab"
    (lab / "infra").mkdir(parents=True)
    (lab / "cleanup.sh").write_bytes((LAB / "cleanup.sh").read_bytes())
    if previous is not None:
        (lab / "infra" / "previous-logging-config.json").write_text(previous, encoding="utf-8")
    calls = tmp_path / "calls.txt"
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "CALLS": str(calls), "AUTO_APPROVE": "1"}
    result = subprocess.run(["bash", str(lab / "cleanup.sh")], env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return calls.read_text(encoding="utf-8").splitlines()


def test_cleanup_destroys_and_resets_transaction_search_it_enabled(tmp_path):
    calls = run_cleanup(tmp_path, "true", previous='{"textDataDeliveryEnabled": true}')
    assert calls[2] == "terraform -chdir=infra destroy -input=false -auto-approve"
    assert calls[3:] == [
        "aws xray update-trace-segment-destination --destination XRay --region eu-west-3",
        "aws logs delete-log-group --log-group-name aws/spans --region eu-west-3",
        "aws bedrock put-model-invocation-logging-configuration "
        "--logging-config file://infra/previous-logging-config.json --region eu-west-3",
    ]


def test_cleanup_leaves_a_preexisting_transaction_search_alone(tmp_path):
    calls = run_cleanup(tmp_path, "false", previous="null")
    assert [c for c in calls if c.startswith("aws")] == []
