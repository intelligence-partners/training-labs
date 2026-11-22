# ingestion.py: reads corpus/, splits by section then by size, writes chunks.jsonl
# Step 3. Tokens are counted with the tokenizer of the embedding model, whose input limit
# is 512 tokens.
import json  # noqa: F401 (used by the TODO)
import re
from pathlib import Path

from decoupage import decouper  # noqa: F401 (used by the TODO)

MODELE_EMBEDDINGS = "intfloat/multilingual-e5-small"


def lire(fichier: Path) -> tuple[dict, str]:
    """Separate the header (key: value) from the Markdown body."""
    brut = fichier.read_text(encoding="utf-8")
    entete, corps = {}, brut
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", brut, re.S)
    if m:
        for ligne in m.group(1).splitlines():
            cle, _, valeur = ligne.partition(":")
            entete[cle.strip()] = valeur.strip()
        corps = m.group(2)
    return entete, corps


def sections(corps: str) -> list[tuple[str, str]]:
    """Split the body at level-2 headings: [(heading, text), ...]."""
    resultat, titre, lignes = [], "Introduction", []
    for ligne in corps.splitlines():
        if ligne.startswith("## "):
            if "".join(lignes).strip():
                resultat.append((titre, "\n".join(lignes)))
            titre, lignes = ligne[3:].strip(), []
        elif not ligne.startswith("# "):
            lignes.append(ligne)
    if "".join(lignes).strip():
        resultat.append((titre, "\n".join(lignes)))
    return resultat


def main() -> None:
    from sentence_transformers import SentenceTransformer   # loaded only for ingestion

    tokenizer = SentenceTransformer(MODELE_EMBEDDINGS).tokenizer

    def compter(texte: str) -> int:
        return len(tokenizer.encode(texte, add_special_tokens=False))

    # TODO(step 3): for each file of sorted(Path("corpus").rglob("*.md")):
    # - read its header and body with lire(), name = path relative to corpus/ (as_posix)
    # - split the body with sections(), then each section with decouper(texte, compter)
    # - one dict per chunk: id f"{nom}#{n}" (n counts the chunks of the file), fichier, titre,
    #   section, version, statut (default "en vigueur"), droits (default "tous"), texte
    # Write one JSON object per line to chunks.jsonl (ensure_ascii=False) and print
    #   f"{len(chunks)} chunks écrits dans chunks.jsonl, issus de {fichiers} fichiers"
    raise NotImplementedError("TODO(step 3): ingestion")


if __name__ == "__main__":
    main()
