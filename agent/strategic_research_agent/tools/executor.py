"""Execute a single research tool call and return normalized evidence rows."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.tools.arxiv import arxiv_search
from strategic_research_agent.tools.tavily_search import tavily_search

logger = logging.getLogger(__name__)


async def execute_research_tool(name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    args = dict(arguments or {})
    if name == "web_search":
        q = str(args.get("query") or "").strip()
        if not q:
            return [{"kind": "error", "tool": name, "message": "empty query"}]
        n = int(args.get("max_results") or settings.max_web_results)
        rows = await asyncio.to_thread(tavily_search, q, n, None)
        return [{"kind": "web", **r} for r in rows]

    if name == "web_search_on_sites":
        q = str(args.get("query") or "").strip()
        domains = args.get("domains")
        if not q:
            return [{"kind": "error", "tool": name, "message": "empty query"}]
        if not isinstance(domains, list) or not domains:
            return [{"kind": "error", "tool": name, "message": "domains required"}]
        doms = [str(d).strip().lstrip("*.") for d in domains[:4] if str(d).strip()]
        n = int(args.get("max_results") or settings.max_web_results)
        rows = await asyncio.to_thread(tavily_search, q, n, doms)
        return [{"kind": "web", **r, "scopedDomains": doms} for r in rows]

    if name == "arxiv_search":
        q = str(args.get("query") or "").strip()
        if not q:
            return [{"kind": "error", "tool": name, "message": "empty query"}]
        n = int(args.get("max_results") or settings.max_arxiv_results)
        items = await arxiv_search(q, n)
        out: list[dict[str, Any]] = []
        for item in items:
            if item.get("error"):
                out.append({"kind": "error", "tool": "arxiv_search", **item})
            else:
                out.append({"kind": "arxiv", **item})
        return out

    if name == "deep_web_research":
        from strategic_research_agent.workflow.subgraphs.web_deep import run_web_deep_research

        q = str(args.get("query") or "").strip()
        if not q:
            return [{"kind": "error", "tool": name, "message": "empty query"}]
        raw_focus = args.get("focus")
        foc: str | None = None
        if raw_focus is not None:
            s = str(raw_focus).strip()
            foc = s or None
        rows = await run_web_deep_research(q, foc)
        return list(rows)

    logger.warning("unknown tool: %s", name)
    return [{"kind": "error", "tool": name, "message": f"unknown tool {name}"}]


def summarize_tool_result_for_llm(rows: list[dict[str, Any]], max_chars: int = 14000) -> str:
    import json

    # Compact: titles + urls + short snippet
    compact: list[dict[str, Any]] = []
    for r in rows[:40]:
        if r.get("kind") == "arxiv" or r.get("source") == "arxiv":
            compact.append(
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "snippet": (r.get("summary") or "")[:600],
                }
            )
        elif r.get("deep_web"):
            compact.append(
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "snippet": (r.get("content") or "")[:2200],
                    "relevance_score": r.get("relevance_score"),
                    "reason": (r.get("relevance_reason") or "")[:400],
                }
            )
        else:
            compact.append(
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "snippet": (r.get("content") or "")[:600],
                }
            )
    text = json.dumps(compact, ensure_ascii=False)
    if len(text) > max_chars:
        return text[:max_chars] + "\n…(truncated)"
    return text
