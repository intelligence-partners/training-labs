"""Steps 5 and 6: the Chroma index and the hybrid search with its filters.

Chroma and rank_bm25 are the real libraries; only the two local models are fakes.
"""

import json
import subprocess
import sys

import chromadb
import pytest
import sentence_transformers
from chromadb.config import Settings

from index import MODELE_EMBEDDINGS, texte_a_indexer
from recherche import DROITS, MODELE_RERANKER, Recherche, fusion_rrf, tokens

PRC = "Que dit la PRC-114 avant un redémarrage ?"
AUGMENTATIONS = "Quelle est l'enveloppe d'augmentations collectives 2026 ?"


# -- step 5: the index -------------------------------------------------------------------------

def test_indexed_text_has_context_title_section_then_chunk():
    chunk = {"titre": "Notes de frais", "section": "Plafonds", "texte": "Un repas..."}
    assert texte_a_indexer(chunk) == "Notes de frais — Plafonds\nUn repas..."
    assert texte_a_indexer(chunk | {"contexte": "Extrait des règles."}) == (
        "Extrait des règles.\nNotes de frais — Plafonds\nUn repas...")


def test_index_holds_18_vectors_of_384_dimensions(indexed, capsys):
    import index

    index.main()  # a second run rebuilds the collection from scratch

    assert capsys.readouterr().out.strip().splitlines()[-1] == "18 vecteurs de 384 dimensions indexés dans ./index"
    collection = chromadb.PersistentClient(path="./index", settings=Settings(anonymized_telemetry=False)) \
        .get_collection("documentation")
    assert collection.count() == 18
    assert collection.metadata == {"modele": MODELE_EMBEDDINGS}
    assert collection.configuration["hnsw"]["space"] == "cosine"
    stored = collection.get(ids=["procedure-prc-114.md#0"], include=["documents", "metadatas"])
    assert stored["documents"][0].startswith("Avant tout redémarrage")  # the chunk only, not the context
    assert stored["metadatas"][0] == {
        "fichier": "procedure-prc-114.md", "titre": "PRC-114 Redémarrage du serveur de facturation",
        "section": "Préalables", "version": "2026-01", "statut": "en vigueur", "droits": "tous"}


# -- step 6: search ------------------------------------------------------------------------------

def test_tokens_keep_identifiers_and_drop_accents_and_stop_words():
    assert tokens(PRC) == ["dit", "prc-114", "avant", "redemarrage"]
    assert tokens("L'Éligibilité au télétravail") == ["l", "eligibilite", "teletravail"]


def test_reciprocal_rank_fusion():
    fused = fusion_rrf([["a", "b", "c"], ["c", "a"]])
    assert fused == ["a", "c", "b"]
    assert fusion_rrf([["x"]], k=0) == ["x"]


def test_models_named_in_the_lesson(indexed):
    Recherche()
    assert MODELE_RERANKER == "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    assert sentence_transformers.LOADED[-2:] == [MODELE_EMBEDDINGS, MODELE_RERANKER]


@pytest.mark.parametrize("hybride", [True, False])
@pytest.mark.parametrize("rerank", [True, False])
def test_employee_never_sees_archived_or_hr_documents(indexed, hybride, rerank):
    r = Recherche()
    for question in (AUGMENTATIONS, "Combien de jours de télétravail ?", "indemnité de connexion"):
        passages = r.rechercher(question, "salarie", hybride=hybride, rerank=rerank)
        assert passages
        assert all(c["statut"] == "en vigueur" and c["droits"] == "tous" for c in passages)
        assert not any(c["fichier"].startswith("archives/") for c in passages)


def test_hr_profile_reaches_the_hr_document(indexed):
    r = Recherche()
    salarie = r.rechercher(AUGMENTATIONS, "salarie")
    rh = r.rechercher(AUGMENTATIONS, "rh")
    assert "remunerations-2026.md" not in {c["fichier"] for c in salarie}
    assert rh[0]["fichier"] == "remunerations-2026.md"
    assert set(DROITS) == {"salarie", "rh"}


def test_identifier_question_ranks_the_procedure_first(indexed):
    passages = Recherche().rechercher(PRC)
    assert passages[0]["id"] == "procedure-prc-114.md#0"
    assert {c["fichier"] for c in passages[:3]} == {"procedure-prc-114.md"}


def test_k_final(indexed):
    r = Recherche()
    assert len(r.rechercher("jours", k_final=5)) == 5
    assert len(r.rechercher("jours", k_final=2)) == 2


def test_cli_output_format(indexed):
    from conftest import TARGET, subprocess_env

    result = subprocess.run([sys.executable, str(TARGET / "recherche.py"), PRC], capture_output=True, text=True,
                            cwd=indexed, env=subprocess_env(), timeout=120)

    assert result.returncode == 0, result.stderr
    first = result.stdout.splitlines()[0]
    assert first == ("1. procedure-prc-114.md#0               Préalables               "
                     "Avant tout redémarrage, obtenez l'accord du responsable d'ex…")


def test_chunks_file_is_the_source_of_truth(indexed):
    r = Recherche()
    lines = [json.loads(line) for line in open("chunks.jsonl", encoding="utf-8")]
    assert list(r.chunks) == [c["id"] for c in lines]
