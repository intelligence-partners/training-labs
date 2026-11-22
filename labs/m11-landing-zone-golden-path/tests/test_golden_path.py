"""Checks on an offline plan of infra/assistant-rh, which calls the ai-service-baseline module."""

import json
import textwrap

import pytest

from conftest import BUDGET_EMAIL
from tfplan import ACCOUNT_ID, all_planned, changes, module_config, references

M = "module.assistant_rh."
MANDATORY_TAGS = {"Service": "assistant-rh", "Team": "rh", "CostCenter": "CC-1042", "DataClassification": "confidentiel"}
LAB_TAGS = {"Projet": "formation-m11", "Environnement": "lab"}
LOG_GROUP_ARN = f"arn:aws:logs:eu-west-3:{ACCOUNT_ID}:log-group:/socle-ia/assistant-rh"


def values(plan, address):
    return all_planned(plan)[address]["values"]


def cfg(plan):
    return module_config(plan, "assistant_rh")


def deferred_document(plan, name):
    """Statements of a policy document read at apply time, by Sid."""
    after = changes(plan)[f"{M}data.aws_iam_policy_document.{name}"]["change"]["after"]
    return {s["sid"]: s for s in after["statement"]}


def test_resources_of_the_golden_path(golden_path_plan):
    managed = sorted(rc["type"] for rc in golden_path_plan["resource_changes"] if rc["mode"] == "managed")
    assert managed == sorted(
        [
            "aws_budgets_budget",
            "aws_cloudwatch_log_group",
            "aws_iam_role",
            "aws_iam_role_policy",
            "aws_kms_alias",
            "aws_kms_key",
            "aws_s3_bucket",
            "aws_s3_bucket_policy",
            "aws_s3_bucket_public_access_block",
            "aws_s3_bucket_server_side_encryption_configuration",
            "aws_s3_bucket_versioning",
        ]
    )
    types = {rc["type"] for rc in golden_path_plan["resource_changes"]}
    assert "aws_iam_role_policy_attachment" not in types
    assert "aws_iam_user" not in types


def test_kms_key_rotation_and_deletion_window(golden_path_plan):
    key = values(golden_path_plan, f"{M}aws_kms_key.this")
    assert key["enable_key_rotation"] is True
    assert key["rotation_period_in_days"] == 365
    assert key["deletion_window_in_days"] == 7
    assert key["description"] == "Key for the assistant-rh service"
    assert values(golden_path_plan, f"{M}aws_kms_alias.this")["name"] == "alias/assistant-rh"


def test_key_policy_lets_cloudwatch_logs_use_the_key_for_this_log_group_only(golden_path_plan):
    policy = json.loads(values(golden_path_plan, f"{M}aws_kms_key.this")["policy"])
    statements = {s["Sid"]: s for s in policy["Statement"]}
    assert set(statements) == {"AccountAdministration", "CloudWatchLogsForThisLogGroup"}
    assert statements["AccountAdministration"]["Principal"] == {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"}

    logs = statements["CloudWatchLogsForThisLogGroup"]
    assert logs["Principal"] == {"Service": "logs.eu-west-3.amazonaws.com"}
    assert sorted(logs["Action"]) == sorted(
        ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:Describe*"]
    )
    assert logs["Condition"] == {"ArnEquals": {"kms:EncryptionContext:aws:logs:arn": LOG_GROUP_ARN}}


def test_bucket_is_private_versioned_and_encrypted_with_the_key(golden_path_plan):
    bucket = values(golden_path_plan, f"{M}aws_s3_bucket.data")
    assert bucket["bucket_prefix"] == "assistant-rh-data-"
    assert bucket["force_destroy"] is True  # ephemeral = true in the lab

    block = values(golden_path_plan, f"{M}aws_s3_bucket_public_access_block.data")
    assert all(block[k] is True for k in ("block_public_acls", "block_public_policy", "ignore_public_acls", "restrict_public_buckets"))

    versioning = values(golden_path_plan, f"{M}aws_s3_bucket_versioning.data")
    assert versioning["versioning_configuration"][0]["status"] == "Enabled"

    sse = values(golden_path_plan, f"{M}aws_s3_bucket_server_side_encryption_configuration.data")
    rule = sse["rule"][0]
    assert rule["bucket_key_enabled"] is True
    assert rule["apply_server_side_encryption_by_default"][0]["sse_algorithm"] == "aws:kms"
    sse_cfg = cfg(golden_path_plan)["aws_s3_bucket_server_side_encryption_configuration.data"]["expressions"]
    assert "aws_kms_key.this.arn" in references(sse_cfg)


def test_bucket_policy_denies_requests_without_tls(golden_path_plan):
    statements = deferred_document(golden_path_plan, "bucket")
    deny = statements["DenyInsecureTransport"]
    assert deny["effect"] == "Deny"
    assert deny["actions"] == ["s3:*"]
    assert deny["principals"] == [{"identifiers": ["*"], "type": "*"}]
    assert deny["condition"] == [{"test": "Bool", "values": ["false"], "variable": "aws:SecureTransport"}]


def test_log_group_is_encrypted_with_bounded_retention(golden_path_plan):
    group = values(golden_path_plan, f"{M}aws_cloudwatch_log_group.this")
    assert group["name"] == "/socle-ia/assistant-rh"
    assert group["retention_in_days"] == 30
    assert group["skip_destroy"] is False  # ephemeral
    assert "aws_kms_key.this.arn" in references(cfg(golden_path_plan)["aws_cloudwatch_log_group.this"]["expressions"]["kms_key_id"])


def test_execution_role(golden_path_plan):
    role = values(golden_path_plan, f"{M}aws_iam_role.runtime")
    assert role["name"] == "assistant-rh-runtime"
    assert role["max_session_duration"] == 3600
    assert role["description"] == "Execution role for the assistant-rh service"
    trust = json.loads(role["assume_role_policy"])
    assert trust["Statement"] == [
        {"Effect": "Allow", "Action": "sts:AssumeRole", "Principal": {"Service": "lambda.amazonaws.com"}}
    ]
    assert values(golden_path_plan, f"{M}aws_iam_role_policy.runtime")["name"] == "assistant-rh-runtime"


def test_runtime_policy_is_least_privilege(golden_path_plan):
    statements = deferred_document(golden_path_plan, "runtime")
    assert {sid: sorted(s["actions"]) for sid, s in statements.items()} == {
        "ListDataBucket": ["s3:ListBucket"],
        "ReadWriteDataObjects": sorted(["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload"]),
        "UseServiceKey": ["kms:Decrypt", "kms:GenerateDataKey"],
        "WriteServiceLogs": ["logs:CreateLogStream", "logs:PutLogEvents"],
    }
    assert all(s["effect"] in (None, "Allow") for s in statements.values())

    # Each statement targets this bucket, this key or this log group: no "*".
    config = cfg(golden_path_plan)["data.aws_iam_policy_document.runtime"]["expressions"]["statement"]
    by_sid = {s["sid"]["constant_value"]: s for s in config}
    assert "aws_s3_bucket.data.arn" in references(by_sid["ListDataBucket"]["resources"])
    assert "aws_s3_bucket.data.arn" in references(by_sid["ReadWriteDataObjects"]["resources"])
    assert "aws_kms_key.this.arn" in references(by_sid["UseServiceKey"]["resources"])
    assert "aws_cloudwatch_log_group.this.arn" in references(by_sid["WriteServiceLogs"]["resources"])
    assert all("constant_value" not in s["resources"] for s in by_sid.values())


def test_budget(golden_path_plan):
    budget = values(golden_path_plan, f"{M}aws_budgets_budget.monthly")
    assert budget["name"] == "assistant-rh-mensuel"
    assert budget["budget_type"] == "COST"
    assert budget["time_unit"] == "MONTHLY"
    assert float(budget["limit_amount"]) == 20
    assert budget["limit_unit"] == "USD"
    notifications = {(n["notification_type"], n["threshold"]) for n in budget["notification"]}
    assert notifications == {("ACTUAL", 80), ("FORECASTED", 100)}
    for notification in budget["notification"]:
        assert notification["comparison_operator"] == "GREATER_THAN"
        assert notification["threshold_type"] == "PERCENTAGE"
        assert notification["subscriber_email_addresses"] == [BUDGET_EMAIL]


def test_every_taggable_resource_has_the_four_mandatory_tags(golden_path_plan):
    taggable = [r for r in all_planned(golden_path_plan).values() if "tags_all" in r["values"]]
    assert {r["type"] for r in taggable} >= {
        "aws_kms_key", "aws_s3_bucket", "aws_cloudwatch_log_group", "aws_iam_role", "aws_budgets_budget",
    }
    for resource in taggable:
        assert resource["values"]["tags"] == MANDATORY_TAGS, resource["address"]
        assert resource["values"]["tags_all"] == {**LAB_TAGS, **MANDATORY_TAGS}, resource["address"]


def test_outputs(golden_path_plan):
    assert set(golden_path_plan["output_changes"]) >= {"bucket_name", "kms_key_id", "log_group_name", "role_arn"}
    assert golden_path_plan["output_changes"]["log_group_name"]["after"] == "/socle-ia/assistant-rh"


# --- The module with other inputs, through a test-only root module -----------

VARIANT = textwrap.dedent(
    """
    provider "aws" {
      region = "eu-west-3"
    }

    module "svc" {
      source = "../modules/ai-service-baseline"

      service_name          = "agent-sav"
      team                  = "sav"
      cost_center           = "CC-2001"
      data_classification   = "interne"
      monthly_budget_usd    = 50
      budget_email          = "sav@example.com"
      trusted_services      = ["bedrock-agentcore.amazonaws.com"]
      bedrock_resource_arns = ["arn:aws:bedrock:eu-west-3::foundation-model/example-model-v1"]
      sse_algorithm         = "%(sse)s"
      %(extra)s
    }
    """
)


def plan_variant(project, sse="aws:kms", extra="", check=True):
    root = project.copy / "infra" / "variant"
    root.mkdir()
    (root / "main.tf").write_text(VARIANT % {"sse": sse, "extra": extra})
    lock = project.copy / "infra" / "assistant-rh" / ".terraform.lock.hcl"
    (root / ".terraform.lock.hcl").write_text(lock.read_text())
    return project.plan("infra/variant", check=check)


def test_module_defaults_keep_data_outside_a_lab(scratch_project):
    plan = plan_variant(scratch_project)
    assert values(plan, "module.svc.aws_s3_bucket.data")["force_destroy"] is False
    assert values(plan, "module.svc.aws_cloudwatch_log_group.this")["skip_destroy"] is True
    trust = json.loads(values(plan, "module.svc.aws_iam_role.runtime")["assume_role_policy"])
    assert trust["Statement"][0]["Principal"] == {"Service": "bedrock-agentcore.amazonaws.com"}

    after = changes(plan)["module.svc.data.aws_iam_policy_document.runtime"]["change"]["after"]
    bedrock = {s["sid"]: s for s in after["statement"]}["InvokeAllowedModels"]
    assert sorted(bedrock["actions"]) == ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    assert bedrock["resources"] == ["arn:aws:bedrock:eu-west-3::foundation-model/example-model-v1"]


def test_dsse_disables_the_bucket_key(scratch_project):
    plan = plan_variant(scratch_project, sse="aws:kms:dsse")
    rule = values(plan, "module.svc.aws_s3_bucket_server_side_encryption_configuration.data")["rule"][0]
    assert rule["apply_server_side_encryption_by_default"][0]["sse_algorithm"] == "aws:kms:dsse"
    assert rule["bucket_key_enabled"] is False


@pytest.mark.parametrize(
    "sse, extra, message",
    [
        ("AES256", "", "Socle IA: every S3 bucket must be encrypted with a KMS key"),
        ("aws:kms", "log_retention_days = 0", "log_retention_days must be one of"),
        ("aws:kms", "kms_deletion_window_days = 3", "kms_deletion_window_days must be between 7 and 30"),
    ],
)
def test_module_guardrails_refuse_non_compliant_inputs(scratch_project, sse, extra, message):
    result = plan_variant(scratch_project, sse=sse, extra=extra, check=False)
    assert not isinstance(result, dict)
    assert message in result.stderr


def test_invalid_service_name_and_classification_are_refused(scratch_project):
    root = scratch_project.copy / "infra" / "variant"
    root.mkdir()
    (root / "main.tf").write_text(
        (VARIANT % {"sse": "aws:kms", "extra": ""})
        .replace('"agent-sav"', '"Agent_SAV"')
        .replace('"interne"', '"secret"')
    )
    (root / ".terraform.lock.hcl").write_text((scratch_project.copy / "infra" / "assistant-rh" / ".terraform.lock.hcl").read_text())
    result = scratch_project.plan("infra/variant", check=False)
    assert not isinstance(result, dict)
    assert "Invalid service_name: kebab-case, 3 to 31 characters." in result.stderr
    assert "data_classification must be public, interne or confidentiel." in result.stderr
