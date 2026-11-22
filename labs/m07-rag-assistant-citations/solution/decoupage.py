# decoupage.py
# Step 3: the sentence chunker from the chunking lesson. It groups whole sentences up to a
# target size and carries the end of the previous chunk over (overlap).
import re
from typing import Callable


def phrases(texte: str) -> list[str]:
    """Split a text into sentences, paragraph by paragraph."""
    morceaux = []
    for paragraphe in re.split(r"\n\s*\n", texte):
        paragraphe = " ".join(paragraphe.split())
        if paragraphe:
            morceaux.extend(p for p in re.split(r"(?<=[.!?»])\s+(?=[A-ZÀ-Ý0-9«])", paragraphe) if p)
    return morceaux


def decouper(texte: str, compter: Callable[[str], int],
             taille_max: int = 200, chevauchement: int = 40) -> list[str]:
    """Group sentences up to taille_max tokens, carrying the last sentences over."""
    chunks, courant = [], []
    for phrase in phrases(texte):
        if courant and compter(" ".join(courant + [phrase])) > taille_max:
            chunks.append(" ".join(courant))
            reprise = []
            for precedente in reversed(courant):
                if compter(" ".join([precedente] + reprise)) > chevauchement:
                    break
                reprise.insert(0, precedente)
            courant = reprise
        courant.append(phrase)
    if courant:
        chunks.append(" ".join(courant))
    return chunks
