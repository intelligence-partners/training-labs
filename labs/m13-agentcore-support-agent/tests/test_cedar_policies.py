"""The three Cedar policies of step 7, evaluated offline with the Cedar engine (cedarpy).

AgentCore Policy adds its own schema validation at deploy time; these tests check the business
rule itself: reads and tickets allowed, refunds up to 5000 cents, never on a B2B order."""

import cedarpy
import pytest

from conftest import SOLUTION

POLICIES = SOLUTION / "SupportLab" / "policies"
GATEWAY_ARN = "arn:aws:bedrock-agentcore:eu-west-3:111122223333:gateway/supportlab-tools-abcdefghij"
PRINCIPAL = 'AgentCore::IamEntity::"arn:aws:iam::111122223333:role/supportlab-agent-runtime"'


def rendered(gateway_arn=GATEWAY_ARN):
    files = ["lecture.template.cedar", "remboursement.template.cedar", "b2b.template.cedar"]
    return "\n".join((POLICIES / name).read_text(encoding="utf-8").replace("GATEWAY_ARN", gateway_arn) for name in files)


def decide(tool, tool_input, resource_arn=GATEWAY_ARN):
    request = {
        "principal": PRINCIPAL,
        "action": f'AgentCore::Action::"{tool}"',
        "resource": f'AgentCore::Gateway::"{resource_arn}"',
        "context": {"input": tool_input},
    }
    result = cedarpy.is_authorized(request, rendered(), [])
    assert not result.diagnostics.errors, result.diagnostics.errors
    return result.decision.value


def test_templates_keep_the_gateway_placeholder():
    for path in POLICIES.glob("*.template.cedar"):
        assert 'AgentCore::Gateway::"GATEWAY_ARN"' in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "tool, tool_input, expected",
    [
        ("support___getOrder", {"orderId": "A-1042"}, "Allow"),
        ("support___createTicket", {"orderId": "A-1042", "summary": "colis abîmé"}, "Allow"),
        ("support___createRefund", {"orderId": "A-1042", "amountCents": 3000, "reason": "colis endommagé"}, "Allow"),
        ("support___createRefund", {"orderId": "A-1042", "amountCents": 5000, "reason": "limite"}, "Allow"),
        ("support___createRefund", {"orderId": "A-1042", "amountCents": 5001, "reason": "au-delà"}, "Deny"),
        ("support___createRefund", {"orderId": "A-1042", "amountCents": 12000, "reason": "colis endommagé"}, "Deny"),
        ("support___createRefund", {"orderId": "B2B-77", "amountCents": 3000, "reason": "professionnel"}, "Deny"),
        ("support___deleteOrder", {"orderId": "A-1042"}, "Deny"),
    ],
    ids=["read", "ticket", "refund-3000", "refund-5000", "refund-5001", "refund-12000", "b2b-forbid", "unknown-tool"],
)
def test_scenario_of_the_lesson(tool, tool_input, expected):
    assert decide(tool, tool_input) == expected


def test_another_gateway_is_not_covered():
    other = GATEWAY_ARN.replace("supportlab-tools", "other-tools")
    assert decide("support___getOrder", {"orderId": "A-1042"}, resource_arn=other) == "Deny"
