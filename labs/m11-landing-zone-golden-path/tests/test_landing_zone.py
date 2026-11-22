"""Checks on an offline plan of infra/landing-zone: OUs, SCPs, attachments, permission sets."""

import json

from conftest import ROOT_ID
from tfplan import all_planned, changes, module_config, references

PLATFORM_ROLE = "arn:aws:iam::*:role/SoclePlatformAdmin"
SSO_PLATFORM_ROLE = "arn:aws:iam::*:role/aws-reserved/sso.amazonaws.com/*/AWSReservedSSO_PlatformAdmin_*"
GLOBAL_SERVICES = [
    "account:*", "budgets:*", "ce:*", "cloudfront:*", "health:*", "iam:*",
    "organizations:*", "route53:*", "sso:*", "sts:*", "support:*",
]
EXPECTED_ATTACHMENTS = {
    "DenyLeaveOrganization": {"Root"},
    "DenyOutsideAllowedRegions": {"Security", "Infrastructure", "Sandbox", "Workloads"},
    "ProtectSecurityBaseline": {"Infrastructure", "Sandbox", "Workloads"},
    "DenyIamUsers": {"Sandbox", "Workloads"},
}


def scps(plan):
    return {
        r["values"]["name"]: r["values"]
        for r in all_planned(plan).values()
        if r["type"] == "aws_organizations_policy"
    }


def statement(plan, name):
    content = json.loads(scps(plan)[name]["content"])
    assert content["Version"] == "2012-10-17"
    assert len(content["Statement"]) == 1
    return content["Statement"][0]


def test_six_organizational_units(landing_zone_plan):
    ous = {a: r["values"] for a, r in all_planned(landing_zone_plan).items() if r["type"] == "aws_organizations_organizational_unit"}
    top = {v["name"]: v for a, v in ous.items() if a.startswith("aws_organizations_organizational_unit.top[")}
    assert set(top) == {"Security", "Infrastructure", "Sandbox", "Workloads"}
    assert all(v["parent_id"] == ROOT_ID for v in top.values())

    children = {v["name"] for a, v in ous.items() if a.startswith("aws_organizations_organizational_unit.workloads[")}
    assert children == {"Dev", "Prod"}
    parent = module_config(landing_zone_plan)["aws_organizations_organizational_unit.workloads"]["expressions"]["parent_id"]
    assert 'aws_organizations_organizational_unit.top["Workloads"].id' in references(parent)


def test_four_service_control_policies(landing_zone_plan):
    policies = scps(landing_zone_plan)
    assert set(policies) == set(EXPECTED_ATTACHMENTS)
    assert all(p["type"] == "SERVICE_CONTROL_POLICY" for p in policies.values())
    assert policies["DenyLeaveOrganization"]["description"] == "Prevents leaving the organization or closing an account"
    assert policies["DenyOutsideAllowedRegions"]["description"] == "Restricts member accounts to the allowed Regions"
    assert policies["ProtectSecurityBaseline"]["description"] == "Prevents disabling logging and detection"
    assert policies["DenyIamUsers"]["description"] == "No IAM users and no long-term access keys"


def test_scp_contents(landing_zone_plan):
    assert statement(landing_zone_plan, "DenyLeaveOrganization") == {
        "Sid": "DenyLeaveOrganizationAndCloseAccount",
        "Effect": "Deny",
        "Action": ["organizations:LeaveOrganization", "account:CloseAccount"],
        "Resource": "*",
    }
    assert statement(landing_zone_plan, "DenyOutsideAllowedRegions") == {
        "Sid": "DenyOutsideAllowedRegions",
        "Effect": "Deny",
        "NotAction": GLOBAL_SERVICES,
        "Resource": "*",
        "Condition": {
            "StringNotEquals": {"aws:RequestedRegion": ["eu-west-3", "eu-west-1"]},
            "ArnNotLike": {"aws:PrincipalArn": [PLATFORM_ROLE]},
        },
    }
    protect = statement(landing_zone_plan, "ProtectSecurityBaseline")
    assert protect["Effect"] == "Deny"
    assert set(protect["Action"]) == {
        "cloudtrail:DeleteTrail", "cloudtrail:StopLogging", "cloudtrail:UpdateTrail",
        "config:DeleteConfigurationRecorder", "config:DeleteDeliveryChannel", "config:StopConfigurationRecorder",
        "guardduty:DeleteDetector", "guardduty:DisassociateFromAdministratorAccount",
        "securityhub:DisableSecurityHub", "access-analyzer:DeleteAnalyzer",
    }
    assert protect["Condition"] == {"ArnNotLike": {"aws:PrincipalArn": [PLATFORM_ROLE]}}
    assert statement(landing_zone_plan, "DenyIamUsers") == {
        "Sid": "DenyIamUsersAndAccessKeys",
        "Effect": "Deny",
        "Action": ["iam:CreateUser", "iam:CreateAccessKey", "iam:CreateLoginProfile"],
        "Resource": "*",
    }


def test_scps_only_deny_and_fit_the_size_limit(landing_zone_plan):
    for name, policy in scps(landing_zone_plan).items():
        content = json.loads(policy["content"])
        assert all(s["Effect"] == "Deny" for s in content["Statement"]), name
        # SCPs are limited to 5,120 characters.
        assert len(json.dumps(content, separators=(",", ":"))) < 5120, name


def test_attachments_target_the_right_ous(landing_zone_plan):
    keys = {a.split('"')[1] for a in all_planned(landing_zone_plan) if a.startswith("aws_organizations_policy_attachment.scp[")}
    expected = {f"{scp}/{target}" for scp, targets in EXPECTED_ATTACHMENTS.items() for target in targets}
    assert keys == expected
    # Only DenyLeaveOrganization touches the root; Security never gets ProtectSecurityBaseline.
    assert {k for k in keys if k.endswith("/Root")} == {"DenyLeaveOrganization/Root"}
    assert "ProtectSecurityBaseline/Security" not in keys

    root = all_planned(landing_zone_plan)['aws_organizations_policy_attachment.scp["DenyLeaveOrganization/Root"]']
    assert root["values"]["target_id"] == ROOT_ID


def test_ous_and_scps_are_tagged(landing_zone_plan):
    for resource in all_planned(landing_zone_plan).values():
        if resource["type"] in ("aws_organizations_organizational_unit", "aws_organizations_policy"):
            assert resource["values"]["tags_all"] == {"Projet": "formation-m11", "Environnement": "lab"}


def test_outputs(landing_zone_plan):
    assert set(landing_zone_plan["output_changes"]) >= {"workloads_ou_id", "dev_ou_id", "prod_ou_id"}


def test_identity_center_is_off_by_default(landing_zone_plan):
    types = {rc["type"] for rc in landing_zone_plan["resource_changes"]}
    assert not any(t.startswith("aws_ssoadmin_") for t in types)


def test_identity_center_permission_sets(landing_zone_sso_plan):
    planned = all_planned(landing_zone_sso_plan)
    sets = {r["values"]["name"]: r["values"] for r in planned.values() if r["type"] == "aws_ssoadmin_permission_set"}
    assert set(sets) == {"PlatformAdmin", "SecurityAudit", "ProdReadOnly", "BillingViewer"}
    assert all(s["session_duration"] == "PT1H" for s in sets.values())
    assert all(s["instance_arn"].startswith("arn:aws:sso:::instance/") for s in sets.values())

    attached = {
        (a.split('"')[1].split("/", 1)[0], r["values"]["managed_policy_arn"])
        for a, r in planned.items()
        if r["type"] == "aws_ssoadmin_managed_policy_attachment"
    }
    assert attached == {
        ("PlatformAdmin", "arn:aws:iam::aws:policy/AdministratorAccess"),
        ("SecurityAudit", "arn:aws:iam::aws:policy/SecurityAudit"),
        ("SecurityAudit", "arn:aws:iam::aws:policy/job-function/ViewOnlyAccess"),
        ("ProdReadOnly", "arn:aws:iam::aws:policy/job-function/ViewOnlyAccess"),
        ("ProdReadOnly", "arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess"),
        ("BillingViewer", "arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess"),
    }


def test_identity_center_platform_role_is_exempt(landing_zone_sso_plan):
    exempt = statement(landing_zone_sso_plan, "ProtectSecurityBaseline")["Condition"]["ArnNotLike"]["aws:PrincipalArn"]
    assert exempt == [PLATFORM_ROLE, SSO_PLATFORM_ROLE]
    regions = statement(landing_zone_sso_plan, "DenyOutsideAllowedRegions")["Condition"]["ArnNotLike"]["aws:PrincipalArn"]
    assert regions == [PLATFORM_ROLE, SSO_PLATFORM_ROLE]


def test_invalid_root_id_is_refused(scratch_project):
    result = scratch_project.plan("infra/landing-zone", {"root_id": "o-notaroot"}, check=False)
    assert not isinstance(result, dict)
    assert "root_id must look like r-ab12" in result.stderr


def test_plan_creates_only(landing_zone_plan):
    assert all(rc["change"]["actions"] in (["create"], ["read"]) for rc in changes(landing_zone_plan).values())
