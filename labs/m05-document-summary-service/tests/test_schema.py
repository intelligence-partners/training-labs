"""Step 2: the schema sent to the API and the Pydantic model that revalidates the output."""

import typing

import pytest
from fake_api import VALID_SUMMARY
from pydantic import ValidationError

from schema import SCHEMA_SYNTHESE, TYPES_DOCUMENT, Synthese


def test_every_property_is_required_and_closed():
    assert set(SCHEMA_SYNTHESE["required"]) == set(SCHEMA_SYNTHESE["properties"])
    assert SCHEMA_SYNTHESE["additionalProperties"] is False
    item = SCHEMA_SYNTHESE["properties"]["chiffres_cles"]["items"]
    assert set(item["required"]) == set(item["properties"])
    assert item["additionalProperties"] is False


def test_schema_and_model_agree_on_document_types():
    literal = typing.get_args(Synthese.model_fields["type_document"].annotation)
    assert list(literal) == TYPES_DOCUMENT == SCHEMA_SYNTHESE["properties"]["type_document"]["enum"]


def test_schema_has_no_reasoning_field():
    # Asking the model to copy its reasoning into the output risks a reasoning_extraction refusal.
    assert not any("raison" in name for name in SCHEMA_SYNTHESE["properties"])


def test_valid_summary_passes():
    synthese = Synthese.model_validate(VALID_SUMMARY)
    assert synthese.chiffres_cles[0].page == 4


def test_unknown_page_is_null():
    data = VALID_SUMMARY | {"chiffres_cles": [{"libelle": "Effectif", "valeur": "310", "page": None}]}
    assert Synthese.model_validate(data).chiffres_cles[0].page is None


@pytest.mark.parametrize(
    "change",
    [
        {"points_cles": ["un", "deux"]},  # fewer than three
        {"points_cles": [str(i) for i in range(8)]},  # more than seven
        {"chiffres_cles": [{"libelle": "x", "valeur": "1", "page": 0}]},  # page must be >= 1
        {"type_document": "lettre"},  # not in the enum
        {"resume": ""},  # empty summary
        {"raisonnement": "..."},  # extra field
    ],
)
def test_business_rules_reject(change):
    with pytest.raises(ValidationError):
        Synthese.model_validate(VALID_SUMMARY | change)
