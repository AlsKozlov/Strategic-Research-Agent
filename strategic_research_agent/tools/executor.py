"""Execute a single research tool call and return normalized evidence rows."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.observability import metrics
from strategic_research_agent.tools.arxiv import arxiv_search
from strategic_research_agent.tools.tavily_search import tavily_search
from strategic_research_agent.tools.wikipedia import wikipedia_search

logger = logging.getLogger(__name__)


async def execute_research_tool(name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    t0 = time.perf_counter()
    outcome = "ok"
    try:
        rows = await _execute_research_tool_inner(name, arguments)
        if rows and all(r.get("kind") == "error" for r in rows):
            outcome = "error"
        elif not rows:
            outcome = "empty"
        return rows
    except Exception:
        outcome = "exception"
        raise
    finally:
        metrics.tool_invocations_total.labels(tool=name, outcome=outcome).inc()
        metrics.tool_latency_seconds.labels(tool=name).observe(time.perf_counter() - t0)


async def _execute_research_tool_inner(name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
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

    if name == "wikipedia_search":
        q = str(args.get("query") or "").strip()
        if not q:
            return [{"kind": "error", "tool": name, "message": "empty query"}]
        n = int(args.get("max_results") or getattr(settings, "max_wikipedia_results", 3))
        items = await wikipedia_search(q, n)
        out2: list[dict[str, Any]] = []
        for item in items:
            if item.get("error"):
                out2.append({"kind": "error", "tool": "wikipedia_search", **item})
            else:
                out2.append({"kind": "wikipedia", **item})
        return out2

    logger.warning("unknown tool: %s", name)
    return [{"kind": "error", "tool": name, "message": f"unknown tool {name}"}]


def summarize_tool_result_for_llm(rows: list[dict[str, Any]], max_chars: int = 14000) -> str:
    import json

    compact: list[dict[str, Any]] = []
    for r in rows[:40]:
        kind = r.get("kind")
        if kind == "arxiv" or r.get("source") == "arxiv":
            compact.append(
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "snippet": (r.get("summary") or "")[:600],
                }
            )
        elif kind == "wikipedia" or r.get("source") == "wikipedia":
            compact.append(
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "description": r.get("description"),
                    "snippet": (r.get("summary") or "")[:1200],
                    "source": "wikipedia",
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
