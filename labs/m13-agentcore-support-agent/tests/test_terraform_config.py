"""Static checks of the two Terraform stacks: the names, settings and permissions the lesson relies
on. `terraform validate` (run by test.sh) checks the syntax against the pinned provider schema."""

import json

import pytest

from conftest import SOLUTION
from tfconfig import TerraformConfig

TERRAFORM = SOLUTION / "terraform"


@pytest.fixture(scope="module")
def api():
    return TerraformConfig(TERRAFORM / "acme-api")


@pytest.fixture(scope="module")
def agent():
    return TerraformConfig(TERRAFORM / "support-agent")


def all_statements(config):
    for document in config.data.get("aws_iam_policy_document", {}).values():
        yield from document.get("statement", [])


def test_providers_are_pinned_exactly(api, agent):
    assert api.required_providers()["aws"] == {"source": "hashicorp/aws", "version": "6.73.0"}
    assert api.required_providers()["archive"] == {"source": "hashicorp/archive", "version": "2.8.1"}
    assert agent.required_providers() == {"aws": {"source": "hashicorp/aws", "version": "6.73.0"}}
    for config in (api, agent):
        assert config.providers["aws"]["default_tags"][0]["tags"]["Lab"] == "m13-agentcore-support-agent"


def test_existing_api_matches_step_1(api):
    function = api.resource("aws_lambda_function", "acme_api")
    assert function["function_name"] == "acme-support-api"
    assert function["runtime"] == "python3.13"
    assert function["handler"] == "app.handler"
    assert function["environment"][0]["variables"] == {"API_KEY": "${var.acme_api_key}"}
    assert api.resource("aws_iam_role", "acme_api")["name"] == "acme-support-api-role"
    assert api.resource("aws_apigatewayv2_api", "acme_api")["name"] == "acme-support-api"
    assert api.resource("aws_lambda_permission", "apigw")["statement_id"] == "apigw-invoke"
    assert api.variables["acme_api_key"]["sensitive"] is True


def test_gateway_tools_with_target_support(agent):
    gateway = agent.resource("aws_bedrockagentcore_gateway", "tools")
    assert gateway["authorizer_type"] == "AWS_IAM"
    assert gateway["protocol_type"] == "MCP"
    assert agent.locals["gateway_name"].endswith("-tools")
    target = agent.resource("aws_bedrockagentcore_gateway_target", "support")
    assert target["name"] == "support"
    api_key = target["credential_provider_configuration"][0]["api_key"][0]
    assert api_key["credential_location"] == "HEADER"
    assert api_key["credential_parameter_name"] == "x-api-key"
    assert "open_api_schema" in target["target_configuration"][0]["mcp"][0]


def test_runtime_is_a_codezip_with_the_cli_environment_names(agent):
    runtime = agent.resource("aws_bedrockagentcore_agent_runtime", "agent")
    code = runtime["agent_runtime_artifact"][0]["code_configuration"][0]
    assert code["entry_point"] == ["opentelemetry-instrument", "main.py"]
    assert code["runtime"] == "PYTHON_3_12"
    assert set(runtime["environment_variables"]) == {"MODEL_ID", "MEMORY_AGENTMEMORY_ID", "AGENTCORE_GATEWAY_TOOLS_URL"}
    assert runtime["network_configuration"][0]["network_mode"] == "PUBLIC"
    assert agent.default("model_id") == "eu.anthropic.claude-opus-5-5"
    assert agent.default("region") == "eu-west-3"


def test_memory_has_the_four_strategies_of_the_template(agent):
    strategies = agent.resources["aws_bedrockagentcore_memory_strategy"]
    assert {s["type"]: s["namespace_templates"] for s in strategies.values()} == {
        "SEMANTIC": ["/users/{actorId}/facts"],
        "USER_PREFERENCE": ["/users/{actorId}/preferences"],
        "SUMMARIZATION": ["/summaries/{actorId}/{sessionId}"],
        "EPISODIC": ["/episodes/{actorId}/{sessionId}"],
    }
    assert agent.locals["memory_name"].endswith("_agentMemory")


def test_policy_engine_and_its_three_policies(agent):
    assert agent.default("enable_policy") is True
    assert agent.locals["cedar_policies"] == {
        "LectureEtTickets": "lecture.template.cedar",
        "RemboursementPlafonne": "remboursement.template.cedar",
        "PasDeRemboursementB2B": "b2b.template.cedar",
    }
    for name in agent.locals["cedar_policies"].values():
        assert (SOLUTION / "SupportLab" / "policies" / name).is_file()
    gateway = agent.resource("aws_bedrockagentcore_gateway", "tools")
    assert gateway["dynamic"][0]["policy_engine_configuration"]["content"][0]["mode"] == "ENFORCE"


def test_online_evaluation_is_optional(agent):
    assert agent.default("enable_online_eval") is False
    config = agent.resource("aws_bedrockagentcore_online_evaluation_config", "support_monitor")
    assert sorted(e["evaluator_id"] for e in config["evaluator"]) == ["Builtin.GoalSuccessRate", "Builtin.Helpfulness"]
    assert config["rule"][0]["sampling_config"][0]["sampling_percentage"] == 100


def test_runtime_reaches_the_model_only_through_the_profile(agent):
    statements = {s["sid"]: s for s in agent.data["aws_iam_policy_document"]["runtime"]["statement"]}
    assert statements["InferenceProfile"]["resources"] == ["${local.profile_arn}"]
    assert statements["DestinationModels"]["condition"][0]["variable"] == "bedrock:InferenceProfileArn"
    assert statements["Gateway"]["resources"] == ["${aws_bedrockagentcore_gateway.tools.gateway_arn}"]
    assert statements["Memory"]["resources"] == ["${aws_bedrockagentcore_memory.agent_memory.arn}"]


def test_no_wildcard_action_and_wildcard_resources_only_where_aws_requires_them(api, agent):
    allowed_star = {"XRayAccess", "CloudWatchMetrics", "GuardrailChecks", "CloudWatchLogDescribe", "CloudWatchQueryGeneration"}
    for config in (api, agent):
        for statement in all_statements(config):
            assert not any(a == "*" or a.endswith(":*") for a in statement["actions"]), statement
            if "*" in statement.get("resources", []):
                assert statement["sid"] in allowed_star, statement


def test_roles_trust_only_agentcore_in_this_account(agent):
    trust = agent.data["aws_iam_policy_document"]["agentcore_trust"]["statement"][0]
    assert trust["principals"][0]["identifiers"] == ["bedrock-agentcore.amazonaws.com"]
    assert {c["variable"] for c in trust["condition"]} == {"aws:SourceAccount", "aws:SourceArn"}


def test_openapi_server_url_is_injected_by_terraform(agent):
    template = json.loads((SOLUTION / "SupportLab" / "schemas" / "acme-support.template.json").read_text(encoding="utf-8"))
    assert agent.locals["openapi_schema"] == "${merge(local.openapi_template, {servers = [{url = var.acme_api_url}]})}"
    assert template["servers"][0]["url"] == "API_URL"
