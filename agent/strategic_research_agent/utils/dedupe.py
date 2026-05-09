from __future__ import annotations

from typing import Any


def evidence_key(e: dict[str, Any]) -> str:
    if e.get("error"):
        return f"err:{id(e)}"
    if e.get("kind") == "arxiv" or e.get("source") == "arxiv":
        return (e.get("url") or e.get("title") or "")[:2048]
    return (e.get("url") or "")[:2048] or f"row:{id(e)}"


def dedupe_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for e in items:
        k = evidence_key(e)
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out
