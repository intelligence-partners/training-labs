"""Steps 2 and 3: the corpus, the sentence chunker and the ingestion into chunks.jsonl."""

import json
from pathlib import Path

import sentence_transformers
from conftest import LAB, TARGET

from decoupage import decouper, phrases
from ingestion import MODELE_EMBEDDINGS, lire, sections


def mots(texte: str) -> int:
    return len(texte.split())


# -- step 2: the corpus -------------------------------------------------------------------------

def test_corpus_has_the_seven_documents_and_the_three_traps():
    files = sorted(p.relative_to(TARGET / "corpus").as_posix() for p in (TARGET / "corpus").rglob("*.md"))
    assert files == [
        "archives/politique-teletravail-2023.md", "conges.md", "notes-de-frais.md", "politique-teletravail.md",
        "procedure-prc-114.md", "remunerations-2026.md", "securite-incidents.md",
    ]
    assert lire(TARGET / "corpus/archives/politique-teletravail-2023.md")[0]["statut"] == "archivé"
    assert lire(TARGET / "corpus/remunerations-2026.md")[0]["droits"] == "rh"
    assert "PRC-114" in lire(TARGET / "corpus/procedure-prc-114.md")[0]["titre"]


def test_starter_and_solution_share_the_same_corpus():
    for path in (LAB / "solution" / "corpus").rglob("*.md"):
        twin = LAB / "starter" / "corpus" / path.relative_to(LAB / "solution" / "corpus")
        assert twin.read_text(encoding="utf-8") == path.read_text(encoding="utf-8")


# -- step 3: chunking ---------------------------------------------------------------------------

def test_sentences_paragraph_by_paragraph():
    texte = "Première phrase. Deuxième phrase ?\n\nNouveau paragraphe ! « Citation » ici. 3 jours.\nSuite."
    assert phrases(texte) == [
        "Première phrase.", "Deuxième phrase ?", "Nouveau paragraphe !", "« Citation » ici.", "3 jours.", "Suite.",
    ]


def test_no_split_before_lowercase():
    assert phrases("Le poste 4410. puis la suite.") == ["Le poste 4410. puis la suite."]


def test_chunks_respect_the_size_and_overlap():
    texte = " ".join(f"Phrase numéro {i} de cinq mots." for i in range(20))
    chunks = decouper(texte, mots, taille_max=20, chevauchement=6)

    assert len(chunks) > 1
    assert all(mots(c) <= 20 for c in chunks)
    for avant, apres in zip(chunks, chunks[1:]):
        derniere = phrases(avant)[-1]
        assert apres.startswith(derniere)  # the last sentence is carried over


def test_a_single_long_sentence_is_never_cut():
    longue = "Une phrase " + "très " * 50 + "longue."
    assert decouper(longue, mots, taille_max=10) == [longue]


def test_header_and_sections():
    entete, corps = lire(TARGET / "corpus/politique-teletravail.md")
    assert entete == {"titre": "Politique de télétravail", "version": "2026-03", "statut": "en vigueur", "droits": "tous"}
    titres = [titre for titre, _ in sections(corps)]
    assert titres == ["Éligibilité", "Rythme", "Équipement et indemnité", "Demande"]


def test_file_without_header(tmp_path):
    fichier = tmp_path / "note.md"
    fichier.write_text("# Titre\n\nTexte libre.\n", encoding="utf-8")
    entete, corps = lire(fichier)
    assert entete == {}
    assert sections(corps) == [("Introduction", "\nTexte libre.")]


def test_ingestion_writes_18_chunks_from_7_files(workdir, capsys):
    import ingestion

    ingestion.main()

    assert capsys.readouterr().out.strip() == "18 chunks écrits dans chunks.jsonl, issus de 7 fichiers"
    chunks = [json.loads(line) for line in Path("chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)) == 18
    assert "politique-teletravail.md#1" in ids
    assert "archives/politique-teletravail-2023.md#0" in ids
    rythme = next(c for c in chunks if c["id"] == "politique-teletravail.md#1")
    assert rythme == {
        "id": "politique-teletravail.md#1",
        "fichier": "politique-teletravail.md",
        "titre": "Politique de télétravail",
        "section": "Rythme",
        "version": "2026-03",
        "statut": "en vigueur",
        "droits": "tous",
        "texte": "Le télétravail est possible jusqu'à trois jours par semaine. Le mardi est un jour de présence "
                 "commun pour toutes les équipes. Le manager peut demander une présence sur site avec un "
                 "préavis de 48 heures.",
    }
    assert MODELE_EMBEDDINGS == "intfloat/multilingual-e5-small"
    assert sentence_transformers.LOADED[-1] == MODELE_EMBEDDINGS  # its tokenizer counts the tokens
