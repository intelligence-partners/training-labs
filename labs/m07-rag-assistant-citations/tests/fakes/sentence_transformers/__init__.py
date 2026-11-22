"""A small, deterministic stand-in for the sentence-transformers package (tests only).

The real package pulls in PyTorch and downloads two models of about 470 MB each. These
fakes keep the same surface the lab uses, so the lab's code runs unchanged offline:

- SentenceTransformer(name).tokenizer.encode(text, add_special_tokens=False)
- SentenceTransformer(name).encode(texts, normalize_embeddings=True, show_progress_bar=False)
  -> numpy array of shape (n, 384), a hashed bag of words (same dimension as multilingual-e5-small)
- CrossEncoder(name).predict([(question, text), ...]) -> numpy array of word-overlap scores

Every model name passed to a constructor is recorded in LOADED, so tests can check that the
lab asks for the models named in the lesson.
"""

import hashlib
import re
import unicodedata

import numpy as np

DIMENSION = 384
LOADED: list[str] = []
# Frequent words a real model gives little weight to.
STOP_WORDS = {"que", "qui", "quoi", "dit", "les", "des", "une", "pour", "avec", "dans", "est", "sont",
              "aux", "par", "sur", "son", "ses", "leur", "elle", "nous", "vous", "tout", "puis"}


def _words(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"^(query|passage): ", "", text)
    return [w for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text) if len(w) > 2 and w not in STOP_WORDS]


class _Tokenizer:
    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        ids = [int(hashlib.md5(w.encode()).hexdigest()[:6], 16) for w in text.split()]
        return [0, *ids, 2] if add_special_tokens else ids


class SentenceTransformer:
    def __init__(self, model_name_or_path: str, *args, **kwargs) -> None:
        LOADED.append(model_name_or_path)
        self.model_name = model_name_or_path
        self.tokenizer = _Tokenizer()

    def encode(self, sentences, normalize_embeddings: bool = False, show_progress_bar=None, **kwargs):
        vectors = np.zeros((len(sentences), DIMENSION), dtype=np.float32)
        for row, sentence in enumerate(sentences):
            for word in _words(sentence):
                stem = word[:6]  # crude stemming: "teletravail" and "teletravaillent" meet
                vectors[row, int(hashlib.md5(stem.encode()).hexdigest(), 16) % DIMENSION] += 1.0
        if normalize_embeddings:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / np.where(norms == 0, 1, norms)
        return vectors


class CrossEncoder:
    def __init__(self, model_name_or_path: str, *args, **kwargs) -> None:
        LOADED.append(model_name_or_path)
        self.model_name = model_name_or_path

    def predict(self, sentences, **kwargs):
        scores = []
        for question, text in sentences:
            q = {w[:6] for w in _words(question)}
            t = {w[:6] for w in _words(text)}
            scores.append(len(q & t) / (len(q) or 1))
        return np.array(scores, dtype=np.float32)
