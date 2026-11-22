# ingestion.py: reads corpus/, splits by section then by size, writes chunks.jsonl
# Step 3. Tokens are counted with the tokenizer of the embedding model, whose input limit
# is 512 tokens.
import json
import re
from pathlib import Path

from decoupage import decouper

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

    chunks = []
    for fichier in sorted(Path("corpus").rglob("*.md")):
        entete, corps = lire(fichier)
        nom = fichier.relative_to("corpus").as_posix()
        n = 0
        for section, texte in sections(corps):
            for morceau in decouper(texte, compter):
                chunks.append({
                    "id": f"{nom}#{n}",
                    "fichier": nom,
                    "titre": entete.get("titre", nom),
                    "section": section,
                    "version": entete.get("version", ""),
                    "statut": entete.get("statut", "en vigueur"),
                    "droits": entete.get("droits", "tous"),
                    "texte": morceau,
                })
                n += 1
    with open("chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    fichiers = len({c["fichier"] for c in chunks})
    print(f"{len(chunks)} chunks écrits dans chunks.jsonl, issus de {fichiers} fichiers")


if __name__ == "__main__":
    main()
