"""The "existing API" (step 1), called with API Gateway HTTP API events."""

import json

from conftest import http_event

KEY = "k" * 48


def test_without_or_with_a_wrong_key_returns_401(acme_api):
    for key in (None, "wrong"):
        result = acme_api.handler(http_event("GET", "/orders/A-1042", key), None)
        assert result["statusCode"] == 401
        assert json.loads(result["body"]) == {"message": "clé API absente ou invalide"}


def test_order_a_1042_is_shipped(acme_api):
    result = acme_api.handler(http_event("GET", "/orders/A-1042", KEY), None)
    assert result["statusCode"] == 200
    # Exactly the second line of the expected output of step 1.
    assert result["body"] == '{"orderId": "A-1042", "status": "expédiée", "carrier": "Colissimo", "totalCents": 18990}'


def test_unknown_order_and_unknown_route(acme_api):
    assert acme_api.handler(http_event("GET", "/orders/Z-0000", KEY), None)["statusCode"] == 404
    assert acme_api.handler(http_event("DELETE", "/orders/A-1042", KEY), None)["statusCode"] == 404


def test_ticket_and_refund(acme_api):
    ticket = acme_api.handler(http_event("POST", "/tickets", KEY, {"orderId": "A-1042", "summary": "colis abîmé"}), None)
    assert ticket["statusCode"] == 201
    assert json.loads(ticket["body"]) == {"ticketId": "T-A-1042", "status": "ouvert", "summary": "colis abîmé"}

    refund = acme_api.handler(http_event("POST", "/refunds", KEY, {"orderId": "A-1042", "amountCents": "3000"}), None)
    assert refund["statusCode"] == 201
    assert json.loads(refund["body"]) == {"refundId": "R-A-1042", "amountCents": 3000, "status": "accepté"}


def test_the_api_itself_has_no_refund_cap(acme_api):
    """The 50 euro rule is not in the API: only Policy enforces it."""
    refund = acme_api.handler(http_event("POST", "/refunds", KEY, {"orderId": "A-1042", "amountCents": "120000"}), None)
    assert refund["statusCode"] == 201
