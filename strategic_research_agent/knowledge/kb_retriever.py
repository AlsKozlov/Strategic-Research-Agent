"""In-memory BM25 retriever for KB chunks passed via A2A metadata.

The platform-api owns the durable RAG store (Qdrant + BM25). When a caller
hands the agent raw KB chunks via ``metadata.kbContext``, we still want to
filter them down to the slice that is actually relevant to the query before
they reach the LLM — otherwise we waste tokens and dilute attention.

This module is intentionally a *retriever*, not a *store*: chunks live for
the duration of one request only, and the BM25 index is built on the fly.
That keeps the agent stateless and matches the architectural rule that the
agent must not hold its own persistent vector store (the platform owns that).

We avoid bringing in heavy deps like ``rank-bm25``: a 50-line BM25
implementation is enough for the chunk counts we expect (≤ a few hundred).
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


@dataclass
class _Doc:
    idx: int
    text: str
    tokens: list[str]
    length: int
    tf: Counter[str]


@dataclass
class KBRetriever:
    """BM25 over a fixed list of chunks. One-shot, request-scoped."""

    k1: float = 1.5
    b: float = 0.75

    _docs: list[_Doc] | None = None
    _df: dict[str, int] | None = None
    _avg_len: float = 0.0
    _idf: dict[str, float] | None = None

    # ── Index ─────────────────────────────────────────────────────────────────

    def fit(self, chunks: list[str]) -> KBRetriever:
        docs: list[_Doc] = []
        for i, raw in enumerate(chunks or []):
            text = (raw or "").strip()
            if not text:
                continue
            toks = _tokenize(text)
            docs.append(
                _Doc(idx=i, text=text, tokens=toks, length=len(toks), tf=Counter(toks))
            )
        self._docs = docs
        if not docs:
            self._df, self._idf, self._avg_len = {}, {}, 0.0
            return self

        df: dict[str, int] = {}
        for d in docs:
            for term in d.tf.keys():
                df[term] = df.get(term, 0) + 1
        self._df = df

        n = len(docs)
        # BM25+ idf with the +1 smoothing to keep weights non-negative.
        self._idf = {
            term: math.log(1 + (n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }
        self._avg_len = sum(d.length for d in docs) / max(1, n)
        return self

    # ── Query ─────────────────────────────────────────────────────────────────

    def _score(self, doc: _Doc, query_terms: list[str]) -> float:
        if not doc.length or not self._idf:
            return 0.0
        score = 0.0
        for term in query_terms:
            tf = doc.tf.get(term, 0)
            if not tf:
                continue
            idf = self._idf.get(term, 0.0)
            denom = tf + self.k1 * (1 - self.b + self.b * doc.length / max(1.0, self._avg_len))
            score += idf * (tf * (self.k1 + 1)) / max(1e-9, denom)
        return score

    def top_k(self, query: str, k: int) -> list[str]:
        if not self._docs:
            return []
        if k <= 0:
            return []
        terms = _tokenize(query)
        if not terms:
            # No usable query terms — fall back to first k chunks deterministically.
            return [d.text for d in self._docs[:k]]
        scored = sorted(
            ((self._score(d, terms), d) for d in self._docs),
            key=lambda p: p[0],
            reverse=True,
        )
        # Drop zero-score docs unless that would leave us with nothing —
        # in which case fall back to the original document order so the
        # caller still sees *something* deterministic.
        nonzero = [doc for score, doc in scored if score > 0]
        if nonzero:
            return [d.text for d in nonzero[:k]]
        return [doc.text for _score, doc in scored[:k]]


def retrieve_kb(query: str, chunks: list[str], top_k: int) -> list[str]:
    """One-shot helper that builds the index and returns the top-k chunks."""
    if not chunks:
        return []
    if len(chunks) <= top_k:
        return list(chunks)
    return KBRetriever().fit(chunks).top_k(query, top_k)


__all__ = ["KBRetriever", "retrieve_kb"]
