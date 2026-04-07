"""Confidence scoring that goes beyond a flat fact count.

The previous heuristic was ``len(evidence) >= 10 → High`` and ignored:

* source authority (a Statista report and a random blog were equal),
* source diversity (10 hits from one domain looked the same as 10 unique),
* contradictions (conflicting numbers had no effect),
* recency (a 2014 link counted as much as a 2025 one).

This module assigns a 0..1 score from those four signals and maps it to
``High | Medium | Low``. It is intentionally rule-based — we want it to be
predictable and explainable, not an LLM call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

# Domains we treat as authoritative for strategic research. The list is
# small on purpose: it is a *prior*, not a whitelist. Anything not in the
# list still contributes, just with a smaller weight.
_HIGH_AUTHORITY = {
    # Public filings + government
    "sec.gov", "europa.eu", "ec.europa.eu", "treasury.gov", "imf.org",
    "worldbank.org", "oecd.org", "bls.gov", "census.gov",
    # Tier-1 financial press
    "ft.com", "bloomberg.com", "reuters.com", "wsj.com", "economist.com",
    # Established research / data
    "statista.com", "gartner.com", "mckinsey.com", "bain.com", "bcg.com",
    "pitchbook.com", "cbinsights.com", "crunchbase.com", "macrotrends.net",
    "grandviewresearch.com", "idc.com",
    # Academic
    "arxiv.org", "semanticscholar.org", "ssrn.com", "nature.com", "science.org",
}

_MEDIUM_AUTHORITY = {
    "techcrunch.com", "theverge.com", "wired.com", "forbes.com",
    "businessinsider.com", "axios.com", "g2.com", "stackshare.io",
    "producthunt.com", "glassdoor.com", "github.com", "wikipedia.org",
}

# Regex for the most common ways evidence carries dates: 2024, 2024-05, 2024/05/12.
_YEAR_RE = re.compile(r"(20\d{2}|19\d{2})")
_NUMBER_RE = re.compile(r"(?:\$|€|£)?\s*\d+(?:[\.,]\d+)?\s*(?:%|bn|m|k|million|billion|thousand)?", re.I)

# Common high-frequency words that would otherwise dominate the topic key
# in _detect_contradictions and create false buckets across unrelated docs.
_STOPWORDS = frozenset(
    {
        "about", "across", "after", "again", "against", "among", "around",
        "based", "because", "before", "being", "below", "between", "beyond",
        "could", "during", "either", "every", "first", "future", "growth",
        "https", "include", "including", "instead", "large", "later", "latest",
        "level", "major", "market", "might", "model", "models", "month",
        "months", "other", "others", "people", "place", "platform", "point",
        "report", "result", "results", "should", "since", "small", "still",
        "study", "their", "there", "these", "thing", "things", "third",
        "those", "three", "today", "users", "value", "value", "version",
        "where", "which", "while", "world", "would", "years",
    }
)


def _domain(url: str) -> str:
    if not url:
        return ""
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _authority(url: str) -> float:
    d = _domain(url)
    if not d:
        return 0.2
    # Match suffixes so subdomains still count (e.g. www2.bls.gov).
    for hi in _HIGH_AUTHORITY:
        if d == hi or d.endswith("." + hi):
            return 1.0
    for md in _MEDIUM_AUTHORITY:
        if d == md or d.endswith("." + md):
            return 0.6
    return 0.35


def _evidence_year(e: dict) -> int | None:
    for key in ("published", "date", "year"):
        v = e.get(key)
        if isinstance(v, (int, float)) and 1900 < v < 2100:
            return int(v)
        if isinstance(v, str):
            m = _YEAR_RE.search(v)
            if m:
                return int(m.group(0))
    text = " ".join(str(e.get(k) or "") for k in ("title", "summary", "content", "snippet"))
    m = _YEAR_RE.search(text)
    return int(m.group(0)) if m else None


def _recency_score(year: int | None, now: int) -> float:
    if year is None:
        return 0.4
    age = max(0, now - year)
    if age <= 1:
        return 1.0
    if age <= 3:
        return 0.8
    if age <= 5:
        return 0.55
    if age <= 10:
        return 0.3
    return 0.1


def _detect_contradictions(evidence: list[dict]) -> int:
    """Cheap signal: count distinct numeric magnitudes that appear across
    different sources for the same noun. We don't try to do real NLI; we
    look for divergent numeric claims that *might* indicate disagreement."""
    if len(evidence) < 2:
        return 0
    buckets: dict[str, set[str]] = {}
    for e in evidence:
        text = " ".join(str(e.get(k) or "") for k in ("title", "summary", "content", "snippet")).lower()
        if not text:
            continue
        # Use the first 3 nontrivial words as a crude topic key, then collect
        # all numeric tokens. Two sources sharing a topic key but differing
        # numerics indicate possible disagreement.
        words = [
            w for w in re.findall(r"[a-zа-яё]+", text)
            if len(w) > 4 and w not in _STOPWORDS
        ]
        if not words:
            continue
        key = " ".join(words[:3])
        nums = set(_NUMBER_RE.findall(text))
        if not nums:
            continue
        buckets.setdefault(key, set()).update(nums)
    contradictions = sum(1 for nums in buckets.values() if len(nums) >= 3)
    return contradictions


@dataclass
class ConfidenceReport:
    label: str
    score: float
    signals: dict[str, float] = field(default_factory=dict)
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "score": round(self.score, 3),
            "signals": {k: round(v, 3) for k, v in self.signals.items()},
            "rationale": list(self.rationale),
        }


def score_confidence(
    evidence: list[dict],
    *,
    citation_integrity: float = 1.0,
    now_year: int | None = None,
) -> ConfidenceReport:
    """Compute a 0..1 confidence score and a label.

    ``citation_integrity`` is the fraction of report links that are backed by
    evidence (see :mod:`governance.citations`). It dampens the score when the
    LLM fabricates URLs.
    """
    rationale: list[str] = []
    n = len(evidence or [])
    if n == 0:
        return ConfidenceReport(
            label="Low",
            score=0.0,
            signals={"volume": 0.0, "authority": 0.0, "diversity": 0.0, "recency": 0.0},
            rationale=["No evidence retrieved."],
        )

    now = now_year or datetime.utcnow().year

    # Volume — diminishing returns at ~12 hits.
    volume = min(1.0, n / 12.0)

    # Authority — average across hits.
    authorities = [_authority(str(e.get("url") or "")) for e in evidence]
    authority = sum(authorities) / len(authorities)

    # Diversity — unique domains as fraction of hits, capped at 1.0.
    domains = {_domain(str(e.get("url") or "")) for e in evidence}
    domains.discard("")
    diversity = min(1.0, len(domains) / max(1, n))
    if len(domains) <= 2 and n >= 4:
        rationale.append(f"Only {len(domains)} unique source domain(s) for {n} hits.")

    # Recency — average across hits.
    recencies = [_recency_score(_evidence_year(e), now) for e in evidence]
    recency = sum(recencies) / len(recencies)

    # Contradictions — penalty.
    contradictions = _detect_contradictions(evidence)
    contradiction_penalty = min(0.25, 0.08 * contradictions)
    if contradictions:
        rationale.append(f"{contradictions} possible numeric disagreement(s) across sources.")

    # Weighted blend, then dampen by citation integrity.
    raw = (
        0.30 * volume
        + 0.30 * authority
        + 0.15 * diversity
        + 0.25 * recency
    )
    score = max(0.0, raw - contradiction_penalty) * citation_integrity

    if citation_integrity < 1.0:
        rationale.append(
            f"Citation integrity {citation_integrity:.2f} (some report URLs missing from evidence)."
        )

    if score >= 0.72:
        label = "High"
    elif score >= 0.45:
        label = "Medium"
    else:
        label = "Low"

    return ConfidenceReport(
        label=label,
        score=score,
        signals={
            "volume": volume,
            "authority": authority,
            "diversity": diversity,
            "recency": recency,
            "contradiction_penalty": contradiction_penalty,
            "citation_integrity": citation_integrity,
        },
        rationale=rationale,
    )


__all__ = ["ConfidenceReport", "score_confidence"]
