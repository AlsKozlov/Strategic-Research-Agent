"""Evidence digest for reflect / synthesize prompts."""

from __future__ import annotations

from typing import Any


def evidence_digest(evidence: list[dict[str, Any]], limit: int = 12000) -> str:
    lines: list[str] = []
    for e in evidence[:80]:
        kind = e.get("kind")
        source = e.get("source") or ""
        if kind == "arxiv" or source == "arxiv":
            lines.append(
                f"- arXiv: {e.get('title')} | {e.get('url')} | {str(e.get('summary', ''))[:400]}"
            )
        elif kind == "wikipedia" or source == "wikipedia":
            lines.append(
                f"- Wikipedia: {e.get('title')} | {e.get('url')} | {str(e.get('summary', ''))[:500]}"
            )
        else:
            lines.append(
                f"- Web: {e.get('title')} | {e.get('url')} | {str(e.get('content', '') or e.get('summary', ''))[:400]}"
            )
    text = "\n".join(lines)
    return text[:limit]
