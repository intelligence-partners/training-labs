"""Step 4 (contextual retrieval) and step 8 (evaluation), against the fake API."""

import json
import re
import sys
from pathlib import Path

import pytest
from fake_api import message

import contextualiser
import evaluation
from contextualiser import CONSIGNE, MODELE, contextualiser as contextualise


# -- step 4 -------------------------------------------------------------------------------------

def test_context_request(fake_api, api_client):
    texte, usage = contextualise("DOC", "Le passage.")

    (body,) = fake_api.requests
    assert MODELE == body["model"] == "claude-haiku-5-5"
    assert body["max_tokens"] == 300
    assert body["thinking"] == {"type": "disabled"}
    assert body["output_config"] == {"effort": "low"}
    document, consigne = body["messages"][0]["content"]
    assert document == {"type": "text", "text": "<document>\nDOC\n</document>", "cache_control": {"type": "ephemeral"}}
    assert consigne == {"type": "text", "text": CONSIGNE.format(chunk="Le passage.")}
    assert texte.startswith("Ce passage traite de")
    assert usage.output_tokens == 30


def test_context_is_empty_when_the_answer_is_cut(fake_api, api_client):
    fake_api.queue.append((200, message([{"type": "text", "text": "Ce pass"}],
                                        {"input_tokens": 1, "output_tokens": 300}, stop_reason="max_tokens")))
    assert contextualise("DOC", "x")[0] == ""


def test_contextualise_the_corpus(indexed, fake_api, api_client, capsys):
    contextualiser.main()

    assert capsys.readouterr().out.strip() == (
        "18 chunks contextualisés, 0 tokens lus depuis le cache, coût estimé 0.0005 $")
    chunks = [json.loads(line) for line in Path("chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(chunks) == 18 and all(c["contexte"].startswith("Ce passage traite de") for c in chunks)
    # The chunks of one document are processed in a row: the document prefix stays identical.
    documents = [r["messages"][0]["content"][0]["text"] for r in fake_api.requests]
    switches = sum(1 for a, b in zip(documents, documents[1:]) if a != b)
    assert switches == 6  # seven documents, six changes


# -- step 8 -------------------------------------------------------------------------------------

def test_the_set_has_eleven_questions():
    assert len(evaluation.JEU) == 11
    assert sum(1 for item in evaluation.JEU if not item["fichiers"]) == 2
    assert {item["profil"] for item in evaluation.JEU} == {"salarie", "rh"}


def test_rank_of_the_first_relevant_passage():
    passages = [{"fichier": "a.md"}, {"fichier": "b.md"}, {"fichier": "a.md"}]
    assert evaluation.rang_premier(passages, ["b.md"]) == 2
    assert evaluation.rang_premier(passages, ["c.md"]) is None


def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["evaluation.py", *argv])
    evaluation.main()


def test_retrieval_only_is_free(indexed, fake_api, api_client, monkeypatch, capsys):
    run(monkeypatch)

    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0].split() == ["question", "rang", "génération"]
    assert len(lines) == 1 + 11 + 2
    assert re.fullmatch(r"Rappel@5 : \d\.\d\d   MRR : \d\.\d\d", lines[-1])
    assert all(line.rstrip().endswith("-") for line in lines[1:12])
    assert fake_api.requests == []


def test_generation_scores_citations_and_abstentions(indexed, fake_api, api_client, monkeypatch, capsys):
    run(monkeypatch, "--generation")

    lines = capsys.readouterr().out.strip().splitlines()
    rows = lines[1:12]
    assert len(fake_api.requests) == 11
    assert re.fullmatch(r"Génération correcte : \d+/11", lines[-1])
    sport = next(r for r in rows if r.startswith("L'entreprise rembourse"))
    augment_salarie = rows[8]
    assert sport.endswith("ok") and augment_salarie.endswith("ok")  # both abstentions are correct


@pytest.mark.parametrize("flag", ["--sans-hybride", "--sans-rerank"])
def test_variants(indexed, monkeypatch, capsys, flag):
    run(monkeypatch, flag)
    assert capsys.readouterr().out.strip().splitlines()[-1].startswith("Rappel@5 : ")


def test_scoring_rules(indexed, fake_api, api_client, monkeypatch, capsys):
    """A cited answer from the wrong file, or an answer that also abstains, is a failure."""
    wrong = {"type": "search_result_location", "source": "kb://conges.md#0", "title": "Congés", "cited_text": "x",
             "search_result_index": 0, "start_block_index": 0, "end_block_index": 1}
    replies = [message([{"type": "text", "text": "Réponse", "citations": [wrong]}],
                       {"input_tokens": 1, "output_tokens": 1})] * 11
    fake_api.queue.extend((200, r) for r in replies)

    run(monkeypatch, "--generation")

    rows = capsys.readouterr().out.strip().splitlines()[1:12]
    verdicts = [row.rsplit(" ", 1)[-1] for row in rows]
    assert verdicts[7] == "ok"  # the compte épargne-temps question expects conges.md
    assert verdicts.count("ÉCHEC") == 10
