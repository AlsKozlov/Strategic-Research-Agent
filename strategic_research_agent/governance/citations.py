"""Post-hoc citation validator for the synthesized research report.

The synthesize node asks the LLM to cite every factual claim with a markdown
link ``[title](url)``. The LLM is, however, perfectly capable of inventing
plausible URLs that were never in the evidence pool. This module:

1. Extracts every markdown link from the report.
2. Compares the URL set against the evidence pool.
3. Reports unsupported URLs and an overall integrity score.
4. Optionally rewrites the report (strict mode) by replacing unsupported
   links with a ``[unverified]`` marker.

The validator is intentionally cheap (regex + set ops) and runs synchronously
inside the engine after the LangGraph returns. We do NOT perform live HEAD
requests on URLs — that would add latency and a third-party dependency we
cannot control. URL liveness is the user's responsibility post-delivery.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# [text](url) — non-greedy text, URL = anything but ')' and whitespace.
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def _normalize_url(url: str) -> str:
    """Strip fragments + trailing punctuation so two textually different URLs
    that point at the same resource compare equal."""
    if not url:
        return ""
    # Drop common trailing punctuation that often sneaks into LLM output.
    url = url.rstrip(".,);")
    try:
        p = urlparse(url)
    except ValueError:
        return url
    if not p.scheme or not p.netloc:
        return url
    netloc = p.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return f"{p.scheme}://{netloc}{path}" + (f"?{p.query}" if p.query else "")


@dataclass
class CitationReport:
    total_links: int = 0
    supported_links: int = 0
    unsupported_urls: list[str] = field(default_factory=list)
    # 0.0 → all citations fabricated; 1.0 → all citations supported.
    integrity_score: float = 1.0

    def to_dict(self) -> dict[str, object]:
        return {
            "total_links": self.total_links,
            "supported_links": self.supported_links,
            "unsupported_urls": list(self.unsupported_urls),
            "integrity_score": round(self.integrity_score, 3),
        }


def _evidence_url_set(evidence: list[dict]) -> set[str]:
    out: set[str] = set()
    for e in evidence or []:
        u = e.get("url") if isinstance(e, dict) else None
        if isinstance(u, str) and u:
            out.add(_normalize_url(u))
    return out


def validate_citations(
    report_markdown: str,
    evidence: list[dict],
    *,
    strict: bool = False,
) -> tuple[str, CitationReport]:
    """Return ``(possibly-rewritten report, report)``.

    In non-strict mode the report text is returned unchanged and the caller
    surfaces ``CitationReport`` to the consumer (e.g. as a caveat).
    In strict mode unsupported links are rewritten to ``[title (unverified)]``
    so the user cannot accidentally trust a fabricated URL.
    """
    rep = CitationReport()
    if not report_markdown:
        return report_markdown, rep

    allowed = _evidence_url_set(evidence)
    if not allowed:
        # No evidence at all — every link is unsupported by definition.
        # Avoid mangling the report; just record the score as 0.
        matches = list(_LINK_RE.finditer(report_markdown))
        rep.total_links = len(matches)
        rep.unsupported_urls = sorted({_normalize_url(m.group(2)) for m in matches})
        rep.integrity_score = 1.0 if rep.total_links == 0 else 0.0
        return report_markdown, rep

    matches = list(_LINK_RE.finditer(report_markdown))
    rep.total_links = len(matches)

    unsupported: set[str] = set()

    def _maybe_replace(m: re.Match[str]) -> str:
        title, url = m.group(1), m.group(2)
        norm = _normalize_url(url)
        if norm in allowed:
            return m.group(0)
        unsupported.add(norm)
        if strict:
            return f"[{title} (unverified)]"
        return m.group(0)

    out = _LINK_RE.sub(_maybe_replace, report_markdown)

    rep.unsupported_urls = sorted(unsupported)
    rep.supported_links = rep.total_links - len(unsupported)
    rep.integrity_score = (
        1.0 if rep.total_links == 0 else rep.supported_links / rep.total_links
    )

    if unsupported:
        logger.info(
            "citation_validator: %d/%d links unsupported (integrity=%.2f)",
            len(unsupported),
            rep.total_links,
            rep.integrity_score,
        )
    return out, rep


__all__ = ["CitationReport", "validate_citations"]
