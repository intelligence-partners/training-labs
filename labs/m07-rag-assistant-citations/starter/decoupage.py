# decoupage.py
# Step 3: the sentence chunker from the chunking lesson. It groups whole sentences up to a
# target size and carries the end of the previous chunk over (overlap).
import re
from typing import Callable


def phrases(texte: str) -> list[str]:
    """Split a text into sentences, paragraph by paragraph."""
    # TODO(step 3): split into paragraphs on blank lines (re.split(r"\n\s*\n", texte)), collapse the
    # whitespace of each paragraph, then split it into sentences after . ! ? or » followed by
    # spaces and an uppercase letter, a digit or «:
    #   re.split(r"(?<=[.!?»])\s+(?=[A-ZÀ-Ý0-9«])", paragraphe)
    raise NotImplementedError("TODO(step 3): phrases")


def decouper(texte: str, compter: Callable[[str], int],
             taille_max: int = 200, chevauchement: int = 40) -> list[str]:
    """Group sentences up to taille_max tokens, carrying the last sentences over."""
    # TODO(step 3): add sentences to the current chunk while compter(...) stays <= taille_max.
    # When the next sentence would overflow, close the chunk and start the next one with the
    # last sentences of the previous chunk, as long as they fit in `chevauchement` tokens.
    # A sentence is never cut, even when it is longer than taille_max on its own.
    raise NotImplementedError("TODO(step 3): decouper")
