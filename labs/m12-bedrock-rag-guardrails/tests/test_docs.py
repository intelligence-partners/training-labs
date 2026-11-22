"""The three fictitious documents and their metadata files, as in step 1 of the lesson."""

import json

import pytest

from conftest import SOLUTION, STARTER

EXPECTED = {"teletravail.md": "RH", "notes-de-frais.md": "RH", "securite-informatique.md": "DSI"}


@pytest.mark.parametrize("variant", [SOLUTION, STARTER], ids=["solution", "starter"])
def test_six_objects_with_valid_metadata(variant):
    docs = variant / "docs"
    assert sorted(p.name for p in docs.iterdir()) == sorted([*EXPECTED, *(f"{name}.metadata.json" for name in EXPECTED)])
    for name, service in EXPECTED.items():
        metadata = json.loads((docs / f"{name}.metadata.json").read_text(encoding="utf-8"))
        assert metadata == {"metadataAttributes": {"service": service, "annee": 2026}}


def test_starter_and_solution_share_the_same_documents():
    for path in (SOLUTION / "docs").iterdir():
        assert (STARTER / "docs" / path.name).read_bytes() == path.read_bytes()


def test_documents_hold_the_facts_the_checkpoints_expect():
    docs = SOLUTION / "docs"
    assert "deux jours par semaine" in (docs / "teletravail.md").read_text(encoding="utf-8")
    assert "25 euros par repas" in (docs / "notes-de-frais.md").read_text(encoding="utf-8")
    assert "01 23 45 67 89" in (docs / "securite-informatique.md").read_text(encoding="utf-8")
