# index.py: computes the embeddings and fills the persistent Chroma index
# Step 5. The indexed text combines the optional context, the title and the section, then the
# chunk: these words help retrieval, even though only the original chunk is sent to Claude.
import json  # noqa: F401 (used by the TODO)

import chromadb  # noqa: F401
from chromadb.config import Settings  # noqa: F401
from sentence_transformers import SentenceTransformer  # noqa: F401

MODELE_EMBEDDINGS = "intfloat/multilingual-e5-small"


def texte_a_indexer(c: dict) -> str:
    """The indexed text: optional context, title, section, then the chunk."""
    # TODO(step 5): join with "\n", skipping empty parts: c.get("contexte", ""),
    # f"{c['titre']} — {c['section']}", then c["texte"].
    raise NotImplementedError("TODO(step 5): texte_a_indexer")


def main() -> None:
    # TODO(step 5):
    # - load chunks.jsonl and encode ["passage: " + texte_a_indexer(c) ...] with
    #   SentenceTransformer(MODELE_EMBEDDINGS).encode(..., normalize_embeddings=True, show_progress_bar=False)
    # - chromadb.PersistentClient(path="./index", settings=Settings(anonymized_telemetry=False))
    # - delete the "documentation" collection if it exists (full reindex), then create it with
    #   configuration={"hnsw": {"space": "cosine"}} and metadata={"modele": MODELE_EMBEDDINGS}
    # - add ids, embeddings, documents (the original chunk text) and metadatas
    #   (fichier, titre, section, version, statut, droits)
    # - print f"{collection.count()} vecteurs de {vecteurs.shape[1]} dimensions indexés dans ./index"
    raise NotImplementedError("TODO(step 5): index")


if __name__ == "__main__":
    main()
