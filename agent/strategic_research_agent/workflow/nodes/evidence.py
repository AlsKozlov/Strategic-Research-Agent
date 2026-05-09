"""Evidence digest for reflect / synthesize prompts."""

from __future__ import annotations

from typing import Any


def evidence_digest(evidence: list[dict[str, Any]], limit: int = 12000) -> str:
    lines: list[str] = []
    for e in evidence[:80]:
        if e.get("kind") == "arxiv" or e.get("source") == "arxiv":
            lines.append(
                f"- arXiv: {e.get('title')} | {e.get('url')} | {str(e.get('summary', ''))[:400]}"
            )
        else:
            lines.append(
                f"- Web: {e.get('title')} | {e.get('url')} | {str(e.get('content', ''))[:400]}"
            )
    text = "\n".join(lines)
    return text[:limit]
