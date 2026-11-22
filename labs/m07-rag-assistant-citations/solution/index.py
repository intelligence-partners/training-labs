# index.py: computes the embeddings and fills the persistent Chroma index
# Step 5. The indexed text combines the optional context, the title and the section, then the
# chunk: these words help retrieval, even though only the original chunk is sent to Claude.
import json

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

MODELE_EMBEDDINGS = "intfloat/multilingual-e5-small"


def texte_a_indexer(c: dict) -> str:
    """The indexed text: optional context, title, section, then the chunk."""
    entete = f"{c['titre']} — {c['section']}"
    return "\n".join(x for x in (c.get("contexte", ""), entete, c["texte"]) if x)


def main() -> None:
    chunks = [json.loads(l) for l in open("chunks.jsonl", encoding="utf-8")]
    encodeur = SentenceTransformer(MODELE_EMBEDDINGS)
    vecteurs = encodeur.encode(["passage: " + texte_a_indexer(c) for c in chunks],
                               normalize_embeddings=True, show_progress_bar=False)

    client = chromadb.PersistentClient(path="./index", settings=Settings(anonymized_telemetry=False))
    try:
        client.delete_collection("documentation")      # full reindex
    except Exception:
        pass
    collection = client.create_collection(
        name="documentation",
        configuration={"hnsw": {"space": "cosine"}},
        metadata={"modele": MODELE_EMBEDDINGS},
    )
    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=vecteurs.tolist(),
        documents=[c["texte"] for c in chunks],
        metadatas=[{k: c[k] for k in ("fichier", "titre", "section", "version", "statut", "droits")}
                   for c in chunks],
    )
    print(f"{collection.count()} vecteurs de {vecteurs.shape[1]} dimensions indexés dans ./index")


if __name__ == "__main__":
    main()
