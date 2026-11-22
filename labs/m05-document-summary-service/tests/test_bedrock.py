"""Optional provider switch: MODEL_PROVIDER=bedrock through the Converse API.

A real boto3 client is wrapped in botocore's Stubber: no network, no credentials, and
every request is validated against the bedrock-runtime service model.
"""

import json
import sys
from pathlib import Path

import boto3
import pytest
from conftest import HAS_PROVIDER_SWITCH

if not HAS_PROVIDER_SWITCH:
    pytest.skip("the optional Bedrock path is in solution/bedrock.py", allow_module_level=True)

from botocore.exceptions import EndpointConnectionError, NoCredentialsError
from botocore.stub import ANY, Stubber
from fake_api import VALID_SUMMARY
from strings import USAGE_FIRST, S, model_line

import bedrock
import main
from schema import SCHEMA_SYNTHESE
from service import CONSIGNES, PROFILS, DemandeRefusee, SortieInvalide, SortieTronquee

MODEL_ID = "test.model-id-from-env"


def converse_response(text: str, stop_reason: str = "end_turn") -> dict:
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 72, "outputTokens": 2914, "totalTokens": 64826,
                  "cacheReadInputTokens": 0, "cacheWriteInputTokens": 61840},
        "metrics": {"latencyMs": 1200},
        "ResponseMetadata": {"RequestId": "11111111-2222-3333-4444-555555555555", "HTTPStatusCode": 200},
    }


@pytest.fixture
def stubbed(monkeypatch):
    client = boto3.client("bedrock-runtime", region_name="eu-west-3",
                          aws_access_key_id="testing", aws_secret_access_key="testing")
    stubber = Stubber(client)
    stubber.activate()
    monkeypatch.setenv("BEDROCK_MODEL_ID", MODEL_ID)
    monkeypatch.setattr(bedrock, "make_client", lambda: client)
    yield stubber
    stubber.deactivate()


def test_request_matches_the_service_model(workdir, stubbed):
    pdf = Path("rapport.pdf")
    expected = bedrock.build_request(MODEL_ID, pdf.read_bytes(), "juridique")
    stubbed.add_response("converse", converse_response(json.dumps(VALID_SUMMARY)), expected)

    resultat = bedrock.synthesize_with_bedrock(pdf, "juridique")

    stubbed.assert_no_pending_responses()
    assert resultat.synthese.model_dump() == VALID_SUMMARY
    assert resultat.model_id == MODEL_ID
    assert resultat.request_id == "11111111-2222-3333-4444-555555555555"


def test_request_content():
    request = bedrock.build_request(MODEL_ID, b"%PDF-1.4", "operationnel")
    assert request["modelId"] == MODEL_ID
    assert request["system"] == [{"text": CONSIGNES}]
    document, cache_point, profile = request["messages"][0]["content"]
    assert document["document"]["format"] == "pdf"
    assert document["document"]["source"] == {"bytes": b"%PDF-1.4"}
    assert cache_point == {"cachePoint": {"type": "default"}}
    assert profile == {"text": PROFILS["operationnel"]}
    schema = request["outputConfig"]["textFormat"]["structure"]["jsonSchema"]["schema"]
    assert json.loads(schema) == SCHEMA_SYNTHESE
    assert request["inferenceConfig"] == {"maxTokens": 16000}


@pytest.mark.parametrize(
    "stop_reason, error, message",
    [
        ("content_filtered", DemandeRefusee, S["declined"]),
        ("guardrail_intervened", DemandeRefusee, S["declined"]),
        ("max_tokens", SortieTronquee, S["truncated"]),
        ("model_context_window_exceeded", SortieTronquee, S["truncated"]),
        ("malformed_model_output", SortieInvalide, S["unexpected"]),
    ],
)
def test_stop_reasons(workdir, stubbed, stop_reason, error, message):
    stubbed.add_response("converse", converse_response('{"tit', stop_reason), {**_any_request()})
    with pytest.raises(error, match=message):
        bedrock.synthesize_with_bedrock(Path("rapport.pdf"), "direction")


def test_invalid_json(workdir, stubbed):
    stubbed.add_response("converse", converse_response(json.dumps(VALID_SUMMARY | {"points_cles": []})),
                         _any_request())
    with pytest.raises(SortieInvalide, match=S["invalid_prefix"]):
        bedrock.synthesize_with_bedrock(Path("rapport.pdf"), "direction")


def test_main_routes_to_bedrock(workdir, stubbed, monkeypatch, capsys):
    stubbed.add_response("converse", converse_response(json.dumps(VALID_SUMMARY)), _any_request())
    monkeypatch.setenv("MODEL_PROVIDER", "bedrock")
    monkeypatch.setattr(sys, "argv", ["main.py", "rapport.pdf", "--profil", "direction"])

    assert main.main() == 0

    out, err = capsys.readouterr()
    assert json.loads(out) == VALID_SUMMARY
    assert err.splitlines()[:2] == [
        model_line(MODEL_ID, "11111111-2222-3333-4444-555555555555"),
        USAGE_FIRST,
    ]
    assert not Path(".fichiers.json").exists()  # no Files API on this path


def test_missing_model_id_exits_2(workdir, monkeypatch, capsys):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    assert bedrock.main_bedrock(Path("rapport.pdf"), "direction") == 2
    assert "BEDROCK_MODEL_ID" in capsys.readouterr().err


@pytest.mark.parametrize(
    "code, status, exit_code",
    [
        ("AccessDeniedException", 403, 4),
        ("ThrottlingException", 429, 5),
        ("ValidationException", 400, 6),
        ("ResourceNotFoundException", 404, 6),
    ],
)
def test_client_errors(workdir, stubbed, code, status, exit_code):
    stubbed.add_client_error("converse", service_error_code=code, service_message="boom", http_status_code=status)
    assert bedrock.main_bedrock(Path("rapport.pdf"), "direction") == exit_code


@pytest.mark.parametrize(
    "error, exit_code",
    [
        (NoCredentialsError(), 4),
        (EndpointConnectionError(endpoint_url="https://bedrock-runtime.eu-west-3.amazonaws.com"), 7),
    ],
)
def test_transport_errors(workdir, monkeypatch, error, exit_code):
    class Failing:
        def converse(self, **_):
            raise error

    monkeypatch.setenv("BEDROCK_MODEL_ID", MODEL_ID)
    assert bedrock.main_bedrock(Path("rapport.pdf"), "direction", client=Failing()) == exit_code


def _any_request() -> dict:
    return {"modelId": MODEL_ID, "system": ANY, "messages": ANY, "inferenceConfig": ANY, "outputConfig": ANY}
