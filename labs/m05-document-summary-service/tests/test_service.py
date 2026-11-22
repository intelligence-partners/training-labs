"""Step 4: the request sent to Claude and the three checks applied to the response."""

import json
import re

import pytest
from anthropic.types.beta import BetaUsage
from fake_api import VALID_SUMMARY, error_body, message_body
from strings import S

import service
from service import (
    CONSIGNES,
    PROFILS,
    DemandeRefusee,
    SortieInvalide,
    SortieTronquee,
    cout_estime,
    synthetiser,
)


def test_request_shape(fake_api, api_client):
    synthetiser("file_011Cabc", "direction")

    (body,) = fake_api.message_requests()
    assert body["model"] == "claude-opus-5-5"
    assert body["max_tokens"] == 16000
    assert body["system"] == CONSIGNES
    assert body["output_config"] == {
        "effort": "medium",
        "format": {"type": "json_schema", "schema": service.SCHEMA_SYNTHESE},
    }
    document, profile = body["messages"][0]["content"]
    assert document == {
        "type": "document",
        "source": {"type": "file", "file_id": "file_011Cabc"},
        "title": S["document_title"],
        "cache_control": {"type": "ephemeral"},
    }
    assert profile == {"type": "text", "text": PROFILS["direction"]}
    assert body["fallbacks"] == "default"
    assert "thinking" not in body  # Opus 5.5 always thinks; effort is the only control
    headers = body["_headers"]
    assert "server-side-fallback-2026-07-01" in headers["anthropic-beta"]
    assert headers["anthropic-version"] == "2026-10-21"


def test_prefix_is_identical_across_profiles(fake_api, api_client):
    for profil in PROFILS:
        synthetiser("file_011Cabc", profil)

    bodies = fake_api.message_requests()
    prefixes = []
    for body in bodies:
        body = {k: v for k, v in body.items() if not k.startswith("_")}
        content = body["messages"][0]["content"]
        prefixes.append(json.dumps({**body, "messages": [{"content": content[:-1]}]}, sort_keys=True))
    assert len(set(prefixes)) == 1
    assert [b["messages"][0]["content"][-1]["text"] for b in bodies] == list(PROFILS.values())


def test_success_returns_summary_model_usage_and_request_id(fake_api, api_client):
    resultat = synthetiser("file_011Cabc", "direction")

    assert resultat.synthese.model_dump() == VALID_SUMMARY
    assert resultat.modele == "claude-opus-5-5"
    assert isinstance(resultat.usage, BetaUsage)
    assert resultat.usage.cache_creation_input_tokens == 61840
    assert resultat.request_id.startswith("req_011C")


def test_text_blocks_are_joined_and_thinking_ignored(fake_api, api_client):
    text = json.dumps(VALID_SUMMARY)
    body = message_body("")
    body["content"] = [
        {"type": "thinking", "thinking": "", "signature": "sig"},
        {"type": "text", "text": text[:40]},
        {"type": "text", "text": text[40:]},
    ]
    fake_api.queue.append((200, body))

    assert synthetiser("file_011Cabc", "juridique").synthese.titre == VALID_SUMMARY["titre"]


def test_refusal_is_reported_with_its_category(fake_api, api_client):
    fake_api.queue.append((200, message_body("", stop_reason="refusal", stop_details={
        "type": "refusal", "category": "cyber", "explanation": "declined"})))

    with pytest.raises(DemandeRefusee, match=S["declined_cyber"]):
        synthetiser("file_011Cabc", "direction")


@pytest.mark.parametrize("stop_reason", ["max_tokens", "model_context_window_exceeded"])
def test_truncation_is_never_parsed(fake_api, api_client, stop_reason):
    fake_api.queue.append((200, message_body('{"titre": "Rapp', stop_reason=stop_reason)))

    with pytest.raises(SortieTronquee, match=re.escape(S["truncated"])):
        synthetiser("file_011Cabc", "direction")


def test_unexpected_stop_reason(fake_api, api_client):
    fake_api.queue.append((200, message_body("", stop_reason="pause_turn")))

    with pytest.raises(SortieInvalide, match=S["unexpected"] + "pause_turn"):
        synthetiser("file_011Cabc", "direction")


@pytest.mark.parametrize(
    "text, errors",
    [
        ("pas du JSON", 1),
        (json.dumps(VALID_SUMMARY | {"points_cles": ["un", "deux"]}), 1),
        (json.dumps(VALID_SUMMARY | {"resume": "", "type_document": "lettre"}), 2),
    ],
)
def test_invalid_output(fake_api, api_client, text, errors):
    fake_api.queue.append((200, message_body(text)))

    with pytest.raises(SortieInvalide, match=S["invalid"].format(n=errors)):
        synthetiser("file_011Cabc", "direction")


def test_unknown_profile_makes_no_call(fake_api, api_client):
    with pytest.raises(ValueError, match=S["unknown_profile"] + "stagiaire"):
        synthetiser("file_011Cabc", "stagiaire")
    assert fake_api.requests == []


def test_api_errors_propagate_to_the_caller(fake_api, api_client):
    import anthropic

    fake_api.queue.append((404, error_body("not_found_error", "File not found")))
    with pytest.raises(anthropic.NotFoundError):
        synthetiser("file_011Cgone", "direction")


def test_cost_matches_the_lesson():
    first = BetaUsage(input_tokens=72, cache_creation_input_tokens=61840, cache_read_input_tokens=0, output_tokens=2914)
    second = BetaUsage(input_tokens=74, cache_creation_input_tokens=0, cache_read_input_tokens=61840, output_tokens=2950)
    assert f"{cout_estime(first):.4f}" == "0.3678"
    assert f"{cout_estime(second):.4f}" == "0.0717"
    # Missing cache fields count as zero.
    assert cout_estime(BetaUsage(input_tokens=1_000_000, output_tokens=0)) == pytest.approx(4.0)


def test_client_settings():
    assert service.client.max_retries == 4
    assert service.client.timeout == 300.0
