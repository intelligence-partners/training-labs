# schema.py
# Step 2: the JSON schema sent to the API, and the Pydantic model that revalidates the output.
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

TYPES_DOCUMENT = ["contrat", "rapport", "appel_d_offres", "proces_verbal", "autre"]

SCHEMA_SYNTHESE = {
    "type": "object",
    "properties": {
        "titre": {"type": "string", "description": "Title of the document as it appears"},
        "type_document": {"type": "string", "enum": TYPES_DOCUMENT},
        "resume": {"type": "string", "description": "Summary in five sentences at most, tailored to the profile"},
        "points_cles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Three to seven points, from most to least important",
        },
        "chiffres_cles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "libelle": {"type": "string"},
                    "valeur": {"type": "string", "description": "Value and unit as written in the document"},
                    "page": {"type": ["integer", "null"], "description": "Page where the figure appears, null if unknown"},
                },
                "required": ["libelle", "valeur", "page"],
                "additionalProperties": False,
            },
        },
        "risques": {"type": "array", "items": {"type": "string"}},
        "questions_ouvertes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Important points the document leaves unanswered",
        },
    },
    "required": ["titre", "type_document", "resume", "points_cles", "chiffres_cles", "risques", "questions_ouvertes"],
    "additionalProperties": False,
}


class ChiffreCle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    libelle: str
    valeur: str
    page: Annotated[int, Field(ge=1)] | None


class Synthese(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titre: str
    type_document: Literal["contrat", "rapport", "appel_d_offres", "proces_verbal", "autre"]
    resume: str = Field(min_length=1)
    points_cles: list[str] = Field(min_length=3, max_length=7)
    chiffres_cles: list[ChiffreCle]
    risques: list[str]
    questions_ouvertes: list[str]
