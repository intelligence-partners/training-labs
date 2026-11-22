# recherche.py: hybrid search (BM25 + vectors), RRF fusion, reranking, filters
# Step 6. The vector search filters by status and rights inside the index; BM25 applies the
# same filter; RRF merges both rankings; the cross-encoder reranks the candidates, reading the
# title and the section with the chunk, like the index.
import argparse
import json
import re
import unicodedata

import chromadb
import numpy as np
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from index import MODELE_EMBEDDINGS, texte_a_indexer

MODELE_RERANKER = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
DROITS = {"salarie": ["tous"], "rh": ["tous", "rh"]}
MOTS_VIDES = {
    "a", "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du", "elle", "en", "est", "et",
    "il", "je", "la", "le", "les", "leur", "lui", "ma", "mais", "me", "mes", "mon", "ne", "nos",
    "notre", "nous", "on", "ou", "par", "pas", "pour", "qu", "que", "qui", "sa", "se", "ses",
    "son", "sont", "sur", "ta", "te", "tes", "ton", "tu", "un", "une", "vos", "votre", "vous", "y",
}


def tokens(texte: str) -> list[str]:
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return [t for t in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", texte) if t not in MOTS_VIDES]


def fusion_rrf(classements: list[list[str]], k: int = 60) -> list[str]:
    # TODO(step 6): reciprocal rank fusion. Each id scores the sum of 1 / (k + rank) over the
    # rankings (rank starts at 1); return the ids sorted by decreasing score.
    raise NotImplementedError("TODO(step 6): fusion_rrf")


class Recherche:
    def __init__(self) -> None:
        self.chunks = {c["id"]: c for c in map(json.loads, open("chunks.jsonl", encoding="utf-8"))}
        self.ids = list(self.chunks)
        self.bm25 = BM25Okapi([tokens(texte_a_indexer(self.chunks[i])) for i in self.ids])
        self.encodeur = SentenceTransformer(MODELE_EMBEDDINGS)
        self.reranker = CrossEncoder(MODELE_RERANKER)
        client = chromadb.PersistentClient(path="./index", settings=Settings(anonymized_telemetry=False))
        self.collection = client.get_collection("documentation")

    def autorise(self, c: dict, profil: str) -> bool:
        # TODO(step 6): a chunk is allowed if it is "en vigueur" and its rights are in DROITS[profil].
        raise NotImplementedError("TODO(step 6): autorise")

    def rechercher(self, question: str, profil: str = "salarie", k_candidats: int = 30,
                   k_final: int = 5, hybride: bool = True, rerank: bool = True) -> list[dict]:
        # TODO(step 6a): vector search filtered by the index itself: encode "query: " + question
        # (normalize_embeddings=True) and query the collection with n_results=k_candidats and
        # where={"$and": [{"statut": "en vigueur"}, {"droits": {"$in": DROITS[profil]}}]}.
        # TODO(step 6b): if hybride, BM25 scores of tokens(question); keep the ids with a score > 0,
        # best first, that autorise() accepts, at most k_candidats.
        # TODO(step 6c): merge with fusion_rrf, keep k_candidats; if rerank, sort them by
        # self.reranker.predict([(question, texte_a_indexer(chunk)), ...]), best first.
        # Return the first k_final chunks (dicts from self.chunks).
        raise NotImplementedError("TODO(step 6): rechercher")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--profil", default="salarie", choices=list(DROITS))
    p.add_argument("--sans-hybride", action="store_true")
    p.add_argument("--sans-rerank", action="store_true")
    a = p.parse_args()
    r = Recherche()
    for rang, c in enumerate(r.rechercher(a.question, a.profil, hybride=not a.sans_hybride,
                                          rerank=not a.sans_rerank), start=1):
        print(f"{rang}. {c['id']:<36} {c['section']:<24} {c['texte'][:60]}…")
