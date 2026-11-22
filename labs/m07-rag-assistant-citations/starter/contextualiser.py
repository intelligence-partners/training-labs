# contextualiser.py: adds to each chunk a context written by Claude Haiku 5.5 (optional)
# Step 4 (optional): Contextual Retrieval. The whole document is the cached prefix; the chunks
# of one document are processed one after the other so the cache stays warm.
import json  # noqa: F401 (used by the TODO)
from collections import defaultdict  # noqa: F401
from pathlib import Path  # noqa: F401

import anthropic

from ingestion import lire  # noqa: F401 (used by the TODO)

client = anthropic.Anthropic()
MODELE = "claude-haiku-5-5"
# Haiku 5.5 prices (prompt under 100,000 tokens), in dollars per million tokens.
PRIX = {"input": 0.10, "cache_write": 0.125, "cache_read": 0.01, "output": 0.50}

CONSIGNE = """Voici le passage à situer dans l'ensemble du document :
<chunk>
{chunk}
</chunk>
Rédige un contexte bref (une ou deux phrases) qui situe ce passage dans le document : de quel
document il s'agit, quelle section, quel sujet. Ce contexte sert uniquement à améliorer la
recherche du passage. Réponds seulement par ce contexte, sans autre texte."""


def contextualiser(document: str, chunk: str) -> tuple[str, object]:
    # TODO(step 4): client.messages.create with model=MODELE, max_tokens=300,
    # thinking={"type": "disabled"}, output_config={"effort": "low"} and one user message:
    # - a text block f"<document>\n{document}\n</document>" with cache_control {"type": "ephemeral"}
    # - a text block CONSIGNE.format(chunk=chunk)
    # If stop_reason is not "end_turn", return ("", usage); otherwise the stripped text and the usage.
    raise NotImplementedError("TODO(step 4): contextualiser")


def main() -> None:
    # TODO(step 4): load chunks.jsonl, group the chunks by file, and for each file read the body of
    # corpus/<file> with lire(); contextualise its chunks one after the other (warm cache), store
    # c["contexte"], add up the tokens read from the cache and the cost with PRIX, rewrite
    # chunks.jsonl and print
    #   f"{len(chunks)} chunks contextualisés, {lus} tokens lus depuis le cache, coût estimé {cout:.4f} $"
    raise NotImplementedError("TODO(step 4): contextualiser main")


if __name__ == "__main__":
    main()
