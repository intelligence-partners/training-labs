"""Unit tests of the vector index builder. HTTP is replaced: nothing reaches OpenSearch."""

import hashlib
import json

import pytest
from botocore.credentials import Credentials

ENDPOINT = "https://abc123.eu-west-3.aoss.amazonaws.com"
BODY = {"settings": {"index": {"knn": True}}, "mappings": {"properties": {}}}
CREDENTIALS = Credentials("AKIDEXAMPLE", "secret", "token")


@pytest.fixture
def no_sleep(index_builder, monkeypatch):
    sleeps = []
    monkeypatch.setattr(index_builder.time, "sleep", sleeps.append)
    return sleeps


def scripted_send(index_builder, monkeypatch, responses):
    calls = []

    def fake_send(method, url, body, region, credentials):
        calls.append((method, url, body))
        return responses.pop(0)

    monkeypatch.setattr(index_builder, "_send", fake_send)
    return calls


def create(index_builder, timeout_seconds=240):
    return index_builder.create_index(ENDPOINT + "/", "kb-index", BODY, "eu-west-3", CREDENTIALS, timeout_seconds, 20)


def test_retries_while_the_data_access_policy_propagates(index_builder, monkeypatch, no_sleep):
    calls = scripted_send(index_builder, monkeypatch, [(403, "forbidden"), (404, ""), (200, "{}"), (200, "")])
    assert create(index_builder) == "created"
    assert [c[0] for c in calls] == ["PUT", "PUT", "PUT", "HEAD"]
    assert calls[0][1] == ENDPOINT + "/kb-index"
    assert calls[0][2] == BODY
    assert no_sleep == [1, 2, 20]


def test_existing_index_is_accepted(index_builder, monkeypatch, no_sleep):
    scripted_send(index_builder, monkeypatch, [(400, '{"error":{"type":"resource_already_exists_exception"}}'), (200, "")])
    assert create(index_builder) == "exists"


def test_waits_until_the_index_is_visible(index_builder, monkeypatch, no_sleep):
    calls = scripted_send(index_builder, monkeypatch, [(200, "{}"), (404, ""), (200, "")])
    assert create(index_builder) == "created"
    assert [c[0] for c in calls] == ["PUT", "HEAD", "HEAD"]


def test_mapping_error_is_not_retried(index_builder, monkeypatch, no_sleep):
    calls = scripted_send(index_builder, monkeypatch, [(400, '{"error":{"type":"mapper_parsing_exception"}}')])
    with pytest.raises(RuntimeError, match="HTTP 400"):
        create(index_builder)
    assert len(calls) == 1


def test_gives_up_after_the_deadline(index_builder, monkeypatch, no_sleep):
    scripted_send(index_builder, monkeypatch, [(403, "forbidden")])
    with pytest.raises(RuntimeError, match="HTTP 403"):
        create(index_builder, timeout_seconds=0)


def test_requests_are_signed_for_opensearch_serverless(index_builder, monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout):
        captured["request"] = request
        return FakeResponse()

    monkeypatch.setattr(index_builder.urllib.request, "urlopen", fake_urlopen)
    status, _ = index_builder._send("PUT", ENDPOINT + "/kb-index", BODY, "eu-west-3", CREDENTIALS)

    request = captured["request"]
    headers = {k.lower(): v for k, v in request.header_items()}
    payload = json.dumps(BODY).encode("utf-8")
    assert status == 200
    assert request.get_method() == "PUT"
    assert request.data == payload
    assert headers["x-amz-content-sha256"] == hashlib.sha256(payload).hexdigest()
    assert "Credential=AKIDEXAMPLE/" in headers["authorization"]
    assert "/eu-west-3/aoss/aws4_request" in headers["authorization"]
    assert "x-amz-content-sha256" in headers["authorization"]
    assert headers["x-amz-security-token"] == "token"


def test_handler_validates_its_input(index_builder):
    with pytest.raises(ValueError, match="endpoint"):
        index_builder.handler({"index": "i", "body": {}}, None)


def test_handler_uses_the_function_region(index_builder, monkeypatch):
    seen = {}

    def fake_create_index(**kwargs):
        seen.update(kwargs)
        return "created"

    monkeypatch.setattr(index_builder, "create_index", fake_create_index)
    monkeypatch.setattr(index_builder, "_credentials", lambda: CREDENTIALS)
    result = index_builder.handler({"endpoint": ENDPOINT, "index": "kb-index", "body": BODY}, None)
    assert result == {"index": "kb-index", "result": "created"}
    assert seen["region"] == "eu-west-3"
    assert seen["timeout_seconds"] == 240.0
