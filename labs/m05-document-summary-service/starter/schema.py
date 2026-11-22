# schema.py
# Step 2: the JSON schema sent to the API, and the Pydantic model that revalidates the output.
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

TYPES_DOCUMENT = ["contrat", "rapport", "appel_d_offres", "proces_verbal", "autre"]

# TODO(step 2): write SCHEMA_SYNTHESE, the JSON schema that constrains generation.
# - properties: titre, type_document (enum TYPES_DOCUMENT), resume, points_cles (array of strings),
#   chiffres_cles (array of {libelle, valeur, page: integer or null}), risques, questions_ouvertes
# - every property in "required", "additionalProperties": False at both levels
# - no "reasoning" field: asking the model to copy its reasoning risks a reasoning_extraction refusal
SCHEMA_SYNTHESE: dict = {}


class ChiffreCle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # TODO(step 2): libelle (str), valeur (str), page (int >= 1, or None)


class Synthese(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # TODO(step 2): the same fields as SCHEMA_SYNTHESE, plus what the schema cannot express:
    # - type_document: Literal["contrat", "rapport", "appel_d_offres", "proces_verbal", "autre"]
    # - resume: at least one character
    # - points_cles: between three and seven items
    # - chiffres_cles: list[ChiffreCle]

