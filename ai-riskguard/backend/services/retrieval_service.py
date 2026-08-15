"""TF-IDF Retrieval Service for AI RiskGuard.

Provides a lightweight local retrieval layer backed by scikit-learn TF-IDF.
No external vector database or embedding model required.

Interface (replaceable):
    Retriever.add_document(doc_id, text)
    Retriever.search(query, top_k) → list of (doc_id, score)
    Retriever.delete_document(doc_id)

A keyword-overlap fallback is used when the corpus is too small for TF-IDF
to produce meaningful results.
"""
from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from collections import Counter
from typing import List, Tuple

logger = logging.getLogger(__name__)

# TF-IDF is only useful with a minimum corpus size
_MIN_TFIDF_DOCS = 3


class Retriever(ABC):
    """Abstract retrieval interface — implementations can be swapped."""

    @abstractmethod
    def add_document(self, doc_id: int, text: str) -> None:
        """Add or update a document in the index."""

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """Return list of (doc_id, score) sorted by descending relevance."""

    @abstractmethod
    def delete_document(self, doc_id: int) -> None:
        """Remove a document from the index."""

    @abstractmethod
    def size(self) -> int:
        """Return number of documents in the index."""


class TFIDFRetriever(Retriever):
    """Local in-memory TF-IDF retrieval backed by scikit-learn.

    Falls back to BM25-style keyword overlap when corpus < MIN_TFIDF_DOCS.
    The index is rebuilt lazily on first search call after any change.
    """

    def __init__(self) -> None:
        self._docs: dict[int, str] = {}   # doc_id → text
        self._dirty: bool = False
        self._vectorizer = None
        self._matrix = None
        self._doc_ids: list[int] = []

    # ── Public interface ──────────────────────────────────────────────────────

    def add_document(self, doc_id: int, text: str) -> None:
        """Insert or replace a document."""
        if text and text.strip():
            self._docs[doc_id] = text.strip()
            self._dirty = True

    def delete_document(self, doc_id: int) -> None:
        """Remove a document from the index."""
        if doc_id in self._docs:
            del self._docs[doc_id]
            self._dirty = True

    def size(self) -> int:
        return len(self._docs)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """Return top-k (doc_id, score) pairs for the given query."""
        if not self._docs:
            return []
        if not query or not query.strip():
            return []

        if len(self._docs) >= _MIN_TFIDF_DOCS:
            return self._tfidf_search(query, top_k)
        return self._keyword_search(query, top_k)

    # ── TF-IDF path ───────────────────────────────────────────────────────────

    def _rebuild_index(self) -> None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            logger.warning("scikit-learn not available; falling back to keyword search.")
            self._vectorizer = None
            self._dirty = False
            return

        self._doc_ids = list(self._docs.keys())
        texts = [self._docs[d] for d in self._doc_ids]
        try:
            vec = TfidfVectorizer(
                stop_words="english",
                max_features=5000,
                ngram_range=(1, 2),
                min_df=1,
            )
            self._matrix = vec.fit_transform(texts)
            self._vectorizer = vec
        except Exception as exc:
            logger.warning("TF-IDF index build failed: %s", exc)
            self._vectorizer = None
        self._dirty = False

    def _tfidf_search(self, query: str, top_k: int) -> List[Tuple[int, float]]:
        if self._dirty or self._vectorizer is None:
            self._rebuild_index()

        if self._vectorizer is None:
            return self._keyword_search(query, top_k)

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            q_vec = self._vectorizer.transform([query])
            scores = cosine_similarity(q_vec, self._matrix).flatten()
            ranked = sorted(
                zip(self._doc_ids, scores.tolist()),
                key=lambda x: x[1],
                reverse=True,
            )
            return [(doc_id, score) for doc_id, score in ranked[:top_k] if score > 0.0]
        except Exception as exc:
            logger.warning("TF-IDF search error: %s", exc)
            return self._keyword_search(query, top_k)

    # ── Keyword-overlap fallback ──────────────────────────────────────────────

    def _keyword_search(self, query: str, top_k: int) -> List[Tuple[int, float]]:
        """BM25-lite: score by keyword overlap when corpus is very small."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        results: list[tuple[int, float]] = []
        for doc_id, text in self._docs.items():
            doc_tokens = self._tokenize(text)
            if not doc_tokens:
                continue
            overlap = sum((Counter(query_tokens) & Counter(doc_tokens)).values())
            score = overlap / math.sqrt(len(doc_tokens))
            if score > 0:
                results.append((doc_id, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace + lowercase tokenizer."""
        return [
            w.lower().strip(".,;:!?\"'()")
            for w in text.split()
            if len(w) > 2
        ]


# Module-level singleton (one per process, rebuilt as evidence is added)
retriever = TFIDFRetriever()
