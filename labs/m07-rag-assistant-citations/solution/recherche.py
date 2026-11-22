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
    scores: dict[str, float] = {}
    for classement in classements:
        for rang, i in enumerate(classement, start=1):
            scores[i] = scores.get(i, 0.0) + 1.0 / (k + rang)
    return sorted(scores, key=scores.get, reverse=True)


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
        return c["statut"] == "en vigueur" and c["droits"] in DROITS[profil]

    def rechercher(self, question: str, profil: str = "salarie", k_candidats: int = 30,
                   k_final: int = 5, hybride: bool = True, rerank: bool = True) -> list[dict]:
        # 1. Vector search, filtered by the index itself.
        q = self.encodeur.encode(["query: " + question], normalize_embeddings=True)[0]
        res = self.collection.query(
            query_embeddings=[q.tolist()],
            n_results=k_candidats,
            where={"$and": [{"statut": "en vigueur"}, {"droits": {"$in": DROITS[profil]}}]},
        )
        semantique = res["ids"][0]
        classements = [semantique]

        # 2. Lexical BM25 search, with the same filter.
        if hybride:
            scores = self.bm25.get_scores(tokens(question))
            ordre = [self.ids[i] for i in np.argsort(scores)[::-1] if scores[i] > 0]
            classements.append([i for i in ordre if self.autorise(self.chunks[i], profil)][:k_candidats])

        # 3. Merge the rankings, then rerank the candidates.
        candidats = fusion_rrf(classements)[:k_candidats]
        if rerank and candidats:
            notes = self.reranker.predict([(question, texte_a_indexer(self.chunks[i])) for i in candidats])
            candidats = [candidats[j] for j in np.argsort(notes)[::-1]]
        return [self.chunks[i] for i in candidats[:k_final]]


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
