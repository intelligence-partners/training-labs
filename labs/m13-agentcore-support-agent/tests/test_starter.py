"""The starter imports cleanly with the pinned SDKs and marks the work of each step."""

import json

from bedrock_agentcore.runtime import RequestContext

from conftest import STARTER


def test_starter_agent_imports_and_answers_with_a_todo(load_agent):
    main = load_agent(variant=STARTER)
    result = main.invoke({"prompt": "Bonjour", "actorId": "c-4821"}, RequestContext(session_id="s" * 40))
    assert "TODO" in result["error"]


def test_starter_helpers_import(load_agent):
    assert load_agent("gateway_client", variant=STARTER).get_gateway_client() is None
    assert load_agent("memory.session", variant=STARTER).get_memory_session_manager("s" * 40, "c-4821") is None


def test_starter_memory_keeps_the_template_threshold_for_the_sed_of_step_5():
    source = (STARTER / "SupportLab" / "app" / "agent" / "memory" / "session.py").read_text(encoding="utf-8")
    assert source.count("relevance_score=0.5") == 4


def test_starter_schema_is_valid_json_with_the_placeholder():
    schema = json.loads((STARTER / "SupportLab" / "schemas" / "acme-support.template.json").read_text(encoding="utf-8"))
    assert schema["servers"] == [{"url": "API_URL"}]


def test_starter_has_todo_markers_for_each_step_to_write():
    expected = {
        "SupportLab/schemas/acme-support.template.json": "TODO (step 3)",
        "terraform/support-agent/gateway.tf": "TODO (step 4)",
        "SupportLab/app/agent/main.py": "TODO (step 5)",
        "SupportLab/app/agent/gateway_client.py": "TODO (step 5)",
        "SupportLab/app/agent/memory/session.py": "TODO (step 5)",
        "terraform/support-agent/runtime.tf": "TODO (step 6)",
        "terraform/support-agent/policy.tf": "TODO (step 7)",
        "SupportLab/policies/remboursement.template.cedar": "TODO (step 7)",
        "SupportLab/policies/b2b.template.cedar": "TODO (step 7)",
    }
    for path, marker in expected.items():
        assert marker in (STARTER / path).read_text(encoding="utf-8"), path


def test_starter_and_solution_share_the_existing_api():
    from conftest import SOLUTION

    assert (STARTER / "acme-api" / "app.py").read_bytes() == (SOLUTION / "acme-api" / "app.py").read_bytes()
