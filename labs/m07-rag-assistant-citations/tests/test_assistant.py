"""Step 7: the cited answer. The real SDK talks to the local fake API."""

from types import SimpleNamespace

import pytest
from anthropic.types.beta import BetaUsage
from fake_api import error_body, message

import assistant
from assistant import ABSTENTION, SYSTEME, bloc_resultat, cout, mettre_en_forme, repondre, sources_citees

CDD = "Je suis en CDD depuis huit mois, ai-je droit au télétravail ?"
SPORT = "L'entreprise rembourse-t-elle les abonnements de salle de sport ?"

PASSAGE = {"id": "politique-teletravail.md#0", "fichier": "politique-teletravail.md",
           "titre": "Politique de télétravail", "section": "Éligibilité", "version": "2026-03",
           "statut": "en vigueur", "droits": "tous", "texte": "Le télétravail est ouvert aux salariés en CDI.",
           "contexte": "Contexte généré, jamais envoyé à Claude."}
RYTHME = PASSAGE | {"id": "politique-teletravail.md#1", "section": "Rythme",
                    "texte": "Le télétravail est possible jusqu'à trois jours par semaine."}


def test_search_result_block():
    assert bloc_resultat(PASSAGE) == {
        "type": "search_result",
        "source": "kb://politique-teletravail.md#0",
        "title": "Politique de télétravail — Éligibilité",
        "content": [{"type": "text", "text": "Le télétravail est ouvert aux salariés en CDI."}],
        "citations": {"enabled": True},
    }


def test_system_prompt_holds_the_exact_abstention_sentence():
    assert f"« {ABSTENTION} »" in SYSTEME
    assert ABSTENTION == "Je ne trouve pas cette information dans la documentation disponible."


def test_request(fake_api, api_client):
    repondre(CDD, [PASSAGE, RYTHME])

    (body,) = fake_api.requests
    assert body["model"] == "claude-opus-5-5"
    assert body["max_tokens"] == 16000
    assert body["system"] == SYSTEME
    assert body["output_config"] == {"effort": "medium"}
    assert body["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in body["_headers"]["anthropic-beta"]
    first, second, question = body["messages"][0]["content"]
    assert first == bloc_resultat(PASSAGE) and second == bloc_resultat(RYTHME)
    assert question == {"type": "text", "text": CDD}  # the question comes after the results
    assert "Contexte généré" not in str(body)


def test_cited_answer_matches_the_lesson(fake_api, api_client):
    reponse = repondre(CDD, [PASSAGE, RYTHME])

    assert mettre_en_forme(reponse) == (
        "Oui. En CDD de plus de six mois, le télétravail est possible avec l'accord écrit de votre manager[1], "
        "jusqu'à trois jours par semaine[2].\n"
        "\n"
        "Sources :\n"
        "[1] Politique de télétravail — Éligibilité (kb://politique-teletravail.md#0)\n"
        "[2] Politique de télétravail — Rythme (kb://politique-teletravail.md#1)"
    )
    assert sources_citees(reponse) == [
        ("kb://politique-teletravail.md#0", "Politique de télétravail — Éligibilité"),
        ("kb://politique-teletravail.md#1", "Politique de télétravail — Rythme"),
    ]
    assert f"{cout(reponse.usage):.4f}" == "0.0100"  # entrée 1450, sortie 210


def test_abstention_has_no_sources(fake_api, api_client):
    reponse = repondre(SPORT, [PASSAGE])
    texte = mettre_en_forme(reponse)
    assert ABSTENTION in texte
    assert "Sources :" not in texte
    assert f"{cout(reponse.usage):.4f}" == "0.0067"  # entrée 1190, sortie 95


@pytest.mark.parametrize("stop_reason, expected", [
    ("refusal", "La demande n'a pas pu être traitée."),
    ("max_tokens", "La réponse a été interrompue : relancez la question."),
])
def test_refusal_and_truncation(fake_api, api_client, stop_reason, expected):
    fake_api.queue.append((200, message([{"type": "text", "text": "Le télé"}],
                                        {"input_tokens": 10, "output_tokens": 5}, stop_reason=stop_reason)))
    assert mettre_en_forme(repondre(CDD, [PASSAGE])) == expected


def test_same_source_is_numbered_once_and_non_text_blocks_are_skipped():
    citation = SimpleNamespace(type="search_result_location", source="kb://a#0", title="A — x")
    other = SimpleNamespace(type="char_location", source=None, title=None)
    reponse = SimpleNamespace(stop_reason="end_turn", content=[
        SimpleNamespace(type="thinking", thinking=""),
        SimpleNamespace(type="text", text="Un", citations=[citation]),
        SimpleNamespace(type="text", text=" et deux", citations=[citation, other]),
        SimpleNamespace(type="text", text=".", citations=None),
    ])
    assert mettre_en_forme(reponse) == "Un[1] et deux[1].\n\nSources :\n[1] A — x (kb://a#0)"


def test_api_errors_are_raised(fake_api, api_client):
    import anthropic

    fake_api.queue.append((529, error_body("overloaded_error", "Overloaded")))
    with pytest.raises(anthropic.APIStatusError):
        repondre(CDD, [PASSAGE])


def test_cost():
    assert cout(BetaUsage(input_tokens=1_000_000, output_tokens=1_000_000)) == pytest.approx(24.0)
    assert cout(BetaUsage(input_tokens=0, output_tokens=0, cache_read_input_tokens=1_000_000,
                          cache_creation_input_tokens=1_000_000)) == pytest.approx(5.2)


def test_module_client_is_the_first_party_sdk():
    import anthropic

    assert isinstance(assistant.client, anthropic.Anthropic)
