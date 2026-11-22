"""Optional provider switch: MODEL_PROVIDER=bedrock through the Converse API.

botocore's Stubber answers converse() and validates each request against the
bedrock-runtime service model: no network, no credentials.
"""

import boto3
import pytest
from botocore.stub import ANY, Stubber
from conftest import HAS_PROVIDER_SWITCH

if not HAS_PROVIDER_SWITCH:
    pytest.skip("the optional Bedrock path is in solution/bedrock.py", allow_module_level=True)

import assistant  # noqa: E402
import bedrock  # noqa: E402
import contextualiser  # noqa: E402

MODEL_ID = "test.answer-model-from-env"
CONTEXT_MODEL_ID = "test.context-model-from-env"
PASSAGES = [
    {"id": "politique-teletravail.md#0", "titre": "Politique de télétravail", "section": "Éligibilité",
     "texte": "Les salariés en CDD de plus de six mois peuvent en bénéficier.", "contexte": "jamais envoyé"},
    {"id": "politique-teletravail.md#1", "titre": "Politique de télétravail", "section": "Rythme",
     "texte": "Le télétravail est possible jusqu'à trois jours par semaine."},
]


def converse_reply(content: list, stop_reason: str = "end_turn") -> dict:
    return {
        "output": {"message": {"role": "assistant", "content": content}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 1450, "outputTokens": 210, "totalTokens": 1660},
        "metrics": {"latencyMs": 900},
    }


def cited(text: str, index: int, with_source: bool = True) -> dict:
    citation = {"location": {"searchResultLocation": {"searchResultIndex": index, "start": 0, "end": 1}},
                "sourceContent": [{"text": PASSAGES[index]["texte"]}]}
    if with_source:
        citation |= {"source": f"kb://{PASSAGES[index]['id']}",
                     "title": f"{PASSAGES[index]['titre']} — {PASSAGES[index]['section']}"}
    return {"citationsContent": {"content": [{"text": text}], "citations": [citation]}}


@pytest.fixture
def stubbed(monkeypatch):
    client = boto3.client("bedrock-runtime", region_name="eu-west-3",
                          aws_access_key_id="testing", aws_secret_access_key="testing")
    monkeypatch.setattr(bedrock, "_client", client)
    monkeypatch.setenv("MODEL_PROVIDER", "bedrock")
    monkeypatch.setenv("BEDROCK_MODEL_ID", MODEL_ID)
    with Stubber(client) as stubber:
        yield stubber


def test_answer_request_and_formatting(stubbed):
    expected = {
        "modelId": MODEL_ID,
        "system": [{"text": assistant.SYSTEME}],
        "messages": [{"role": "user", "content": [
            {"searchResult": {"source": "kb://politique-teletravail.md#0",
                              "title": "Politique de télétravail — Éligibilité",
                              "content": [{"text": PASSAGES[0]["texte"]}], "citations": {"enabled": True}}},
            {"searchResult": {"source": "kb://politique-teletravail.md#1",
                              "title": "Politique de télétravail — Rythme",
                              "content": [{"text": PASSAGES[1]["texte"]}], "citations": {"enabled": True}}},
            {"text": "Ai-je droit au télétravail ?"},
        ]}],
        "inferenceConfig": {"maxTokens": 16000},
    }
    stubbed.add_response("converse", converse_reply([
        {"reasoningContent": {"reasoningText": {"text": "...", "signature": "sig"}}},
        cited("Oui, avec l'accord écrit de votre manager", 0),
        cited(", jusqu'à trois jours par semaine", 1, with_source=False),  # source looked up by index
        {"text": "."},
    ]), expected)

    reponse = assistant.repondre("Ai-je droit au télétravail ?", PASSAGES)  # the switch is inside repondre()

    stubbed.assert_no_pending_responses()
    assert reponse.model == MODEL_ID
    assert assistant.mettre_en_forme(reponse) == (
        "Oui, avec l'accord écrit de votre manager[1], jusqu'à trois jours par semaine[2].\n\n"
        "Sources :\n"
        "[1] Politique de télétravail — Éligibilité (kb://politique-teletravail.md#0)\n"
        "[2] Politique de télétravail — Rythme (kb://politique-teletravail.md#1)"
    )
    assert (reponse.usage.input_tokens, reponse.usage.output_tokens) == (1450, 210)


@pytest.mark.parametrize("stop_reason, expected", [
    ("content_filtered", "La demande n'a pas pu être traitée."),
    ("guardrail_intervened", "La demande n'a pas pu être traitée."),
    ("max_tokens", "La réponse a été interrompue : relancez la question."),
])
def test_stop_reasons(stubbed, stop_reason, expected):
    stubbed.add_response("converse", converse_reply([{"text": "x"}], stop_reason), {
        "modelId": MODEL_ID, "system": ANY, "messages": ANY, "inferenceConfig": ANY})
    assert assistant.mettre_en_forme(assistant.repondre("?", PASSAGES)) == expected


def test_abstention_without_citation(stubbed):
    stubbed.add_response("converse", converse_reply([{"text": f"« {assistant.ABSTENTION} »"}]), {
        "modelId": MODEL_ID, "system": ANY, "messages": ANY, "inferenceConfig": ANY})
    reponse = assistant.repondre("Salle de sport ?", PASSAGES)
    assert assistant.sources_citees(reponse) == []
    assert "Sources :" not in assistant.mettre_en_forme(reponse)


def test_contextualisation_uses_a_cache_point_and_its_own_model(stubbed, monkeypatch):
    monkeypatch.setenv("BEDROCK_CONTEXT_MODEL_ID", CONTEXT_MODEL_ID)
    stubbed.add_response("converse", {
        **converse_reply([{"text": " Extrait de la politique de télétravail. "}]),
        "usage": {"inputTokens": 20, "outputTokens": 12, "totalTokens": 1032,
                  "cacheReadInputTokens": 1000, "cacheWriteInputTokens": 0},
    }, {
        "modelId": CONTEXT_MODEL_ID,
        "messages": [{"role": "user", "content": [
            {"text": "<document>\nDOC\n</document>"},
            {"cachePoint": {"type": "default"}},
            {"text": contextualiser.CONSIGNE.format(chunk="Le passage.")},
        ]}],
        "inferenceConfig": {"maxTokens": 300},
    })

    texte, usage = contextualiser.contextualiser("DOC", "Le passage.")

    assert texte == "Extrait de la politique de télétravail."
    assert usage.cache_read_input_tokens == 1000


def test_context_model_defaults_to_the_answer_model(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", MODEL_ID)
    monkeypatch.delenv("BEDROCK_CONTEXT_MODEL_ID", raising=False)
    assert bedrock.model_id("BEDROCK_CONTEXT_MODEL_ID") == MODEL_ID


def test_missing_model_id_and_unknown_provider(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    with pytest.raises(SystemExit, match="BEDROCK_MODEL_ID"):
        bedrock.model_id()
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    with pytest.raises(SystemExit, match="MODEL_PROVIDER"):
        bedrock.provider()


def test_default_provider_is_anthropic(monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    assert bedrock.provider() == "anthropic"
