"""Checks on an offline `terraform plan` of infra/ (fake credentials, no AWS call)."""

from conftest import TARGET_DIR
from tfplan import changes, config, planned, references

LAB_TAGS = {"Projet": "formation-m10", "Environnement": "lab"}


def values(plan, address):
    return planned(plan)[address]["values"]


def test_plan_creates_exactly_the_lab_resources(plan):
    types = sorted(rc["type"] for rc in plan["resource_changes"] if rc["mode"] == "managed")
    assert types == sorted(
        [
            "aws_apigatewayv2_api",
            "aws_apigatewayv2_integration",
            "aws_apigatewayv2_route",
            "aws_apigatewayv2_route",
            "aws_apigatewayv2_stage",
            "aws_cloudwatch_log_group",
            "aws_dynamodb_table",
            "aws_iam_role",
            "aws_iam_role_policy",
            "aws_lambda_function",
            "aws_lambda_permission",
            "aws_lambda_permission",
        ]
    )
    assert all(rc["change"]["actions"] == ["create"] for rc in plan["resource_changes"] if rc["mode"] == "managed")


def test_no_hourly_billed_resource_and_no_iam_user(plan):
    types = {rc["type"] for rc in plan["resource_changes"]}
    assert not types & {"aws_nat_gateway", "aws_instance", "aws_vpc_endpoint", "aws_iam_user", "aws_iam_access_key"}


def test_table_is_on_demand_with_a_string_id(plan):
    table = values(plan, "aws_dynamodb_table.prompts")
    assert table["name"] == "registre-prompts"
    assert table["billing_mode"] == "PAY_PER_REQUEST"
    assert table["hash_key"] == "id"
    assert table["attribute"] == [{"name": "id", "type": "S"}]


def test_log_group_is_kept_seven_days(plan):
    group = values(plan, "aws_cloudwatch_log_group.prompts")
    assert group["name"] == "/aws/lambda/registre-prompts-prompts"
    assert group["retention_in_days"] == 7


def test_function_configuration(plan):
    function = values(plan, "aws_lambda_function.prompts")
    assert function["function_name"] == "registre-prompts-prompts"
    assert function["runtime"] == "python3.13"
    assert function["architectures"] == ["arm64"]
    assert function["handler"] == "app.handler"
    assert function["memory_size"] == 256
    assert function["timeout"] == 10
    assert function["environment"] == [{"variables": {"TABLE_NAME": "registre-prompts"}}]
    assert function["logging_config"] == [
        {
            "log_format": "JSON",
            "application_log_level": "INFO",
            "system_log_level": "INFO",
            "log_group": "/aws/lambda/registre-prompts-prompts",
        }
    ]
    expressions = config(plan)["aws_lambda_function.prompts"]["expressions"]
    assert "aws_iam_role.prompts_function.arn" in references(expressions["role"])


def test_role_trusts_lambda_only_and_has_no_managed_policy(plan):
    role = values(plan, "aws_iam_role.prompts_function")
    assert role.get("managed_policy_arns") in (None, [])
    types = {rc["type"] for rc in plan["resource_changes"]}
    assert "aws_iam_role_policy_attachment" not in types
    assert "aws_iam_role_policy_attachments_exclusive" not in types
    # The trust policy is fully known at plan time.
    trust = role["assume_role_policy"]
    assert '"Service":"lambda.amazonaws.com"' in trust.replace(" ", "")
    assert '"Action":"sts:AssumeRole"' in trust.replace(" ", "")


def test_inline_policy_is_least_privilege(plan):
    policy = values(plan, "aws_iam_role_policy.minimal")
    assert policy["name"] == "registre-prompts-minimal"

    document = changes(plan)["data.aws_iam_policy_document.minimal"]["change"]["after"]
    statements = {s["sid"]: s for s in document["statement"]}
    assert set(statements) == {"RegistryTable", "FunctionLogs"}
    assert sorted(statements["RegistryTable"]["actions"]) == ["dynamodb:GetItem", "dynamodb:PutItem"]
    assert sorted(statements["FunctionLogs"]["actions"]) == ["logs:CreateLogStream", "logs:PutLogEvents"]
    assert all(s["effect"] in (None, "Allow") for s in statements.values())
    assert all(not s["not_actions"] and not s["not_resources"] for s in statements.values())

    # Resources: the ARN of this table and of this log group, never "*".
    cfg = config(plan)["data.aws_iam_policy_document.minimal"]["expressions"]["statement"]
    by_sid = {s["sid"]["constant_value"]: s for s in cfg}
    assert references(by_sid["RegistryTable"]["resources"]) >= {"aws_dynamodb_table.prompts.arn"}
    assert references(by_sid["FunctionLogs"]["resources"]) >= {"aws_cloudwatch_log_group.prompts.arn"}
    assert "constant_value" not in by_sid["RegistryTable"]["resources"]
    assert "constant_value" not in by_sid["FunctionLogs"]["resources"]


def test_no_create_log_group_permission(plan):
    document = changes(plan)["data.aws_iam_policy_document.minimal"]["change"]["after"]
    actions = {action for statement in document["statement"] for action in statement["actions"]}
    assert "logs:CreateLogGroup" not in actions
    assert not any("*" in action for action in actions)


def test_http_api_routes_and_throttling(plan):
    api = values(plan, "aws_apigatewayv2_api.prompts")
    assert api["protocol_type"] == "HTTP"

    stage = values(plan, "aws_apigatewayv2_stage.default")
    assert stage["name"] == "$default"
    assert stage["auto_deploy"] is True
    settings = stage["default_route_settings"][0]
    assert settings["throttling_burst_limit"] == 10
    assert settings["throttling_rate_limit"] == 5

    routes = {values(plan, a)["route_key"] for a in planned(plan) if a.startswith("aws_apigatewayv2_route.")}
    assert routes == {"POST /prompts", "GET /prompts/{id}"}

    integration = values(plan, "aws_apigatewayv2_integration.prompts")
    assert integration["integration_type"] == "AWS_PROXY"
    assert integration["payload_format_version"] == "2.0"


def test_api_gateway_may_invoke_only_the_two_routes(plan):
    cfg = config(plan)
    permissions = [a for a in cfg if cfg[a]["type"] == "aws_lambda_permission"]
    assert len(permissions) == 2
    for address in permissions:
        permission = values(plan, address)
        assert permission["principal"] == "apigateway.amazonaws.com"
        assert permission["action"] == "lambda:InvokeFunction"
        # source_arn is only known after apply: check that it is set and scoped to this API.
        assert "aws_apigatewayv2_api.prompts.execution_arn" in references(cfg[address]["expressions"]["source_arn"])

    # And scoped to each route's method and path, as written in the configuration.
    source = "".join(p.read_text() for p in sorted((TARGET_DIR / "infra").glob("*.tf")))
    assert 'execution_arn}/*/POST/prompts"' in source
    assert 'execution_arn}/*/GET/prompts/*"' in source


def test_resources_carry_the_cost_tags(plan):
    taggable = [r for r in planned(plan).values() if "tags_all" in r["values"]]
    assert len(taggable) >= 6
    for resource in taggable:
        assert resource["values"]["tags_all"] == LAB_TAGS, resource["address"]


def test_outputs(plan):
    assert set(plan["output_changes"]) >= {"api_url", "table_name"}
    assert plan["output_changes"]["table_name"]["after"] == "registre-prompts"
