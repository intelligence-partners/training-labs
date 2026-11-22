"""The OpenAPI description of the existing API (step 3) and the tools it becomes (step 6)."""

import json

import pytest

from conftest import SOLUTION, http_event

TEMPLATE = SOLUTION / "SupportLab" / "schemas" / "acme-support.template.json"
KEY = "k" * 48


@pytest.fixture(scope="module")
def schema():
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def operations(schema):
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            yield path, method, operation


def test_template_keeps_the_placeholder_for_the_static_server_url(schema):
    assert schema["openapi"] == "3.0.3"
    assert schema["servers"] == [{"url": "API_URL"}]


def test_three_operations_become_three_tools_of_target_support(schema):
    tools = sorted(f"support___{operation['operationId']}" for _, _, operation in operations(schema))
    assert tools == ["support___createRefund", "support___createTicket", "support___getOrder"]
    for _, _, operation in operations(schema):
        assert operation["description"]


def test_parameters_are_in_path_or_query_and_the_amount_is_an_integer(schema):
    for _, _, operation in operations(schema):
        for parameter in operation["parameters"]:
            assert parameter["in"] in ("path", "query")
            assert parameter["required"] is True
    refund = schema["paths"]["/refunds"]["post"]
    amount = next(p for p in refund["parameters"] if p["name"] == "amountCents")
    assert amount["schema"] == {"type": "integer"}


def test_every_operation_is_served_by_the_existing_api(schema, acme_api):
    samples = {"orderId": "A-1042", "summary": "colis abîmé", "amountCents": "3000", "reason": "colis endommagé"}
    for path, method, operation in operations(schema):
        query = {p["name"]: samples[p["name"]] for p in operation["parameters"] if p["in"] == "query"} or None
        concrete = path.replace("{orderId}", samples["orderId"])
        result = acme_api.handler(http_event(method.upper(), concrete, KEY, query), None)
        assert result["statusCode"] in {int(code) for code in operation["responses"]}, operation["operationId"]
