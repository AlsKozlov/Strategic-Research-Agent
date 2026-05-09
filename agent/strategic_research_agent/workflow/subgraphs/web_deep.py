"""LangGraph subgraph: Tavily advanced → fetch/extract → relevance → optional refine loop."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from strategic_research_agent.config import settings
from strategic_research_agent.tools.content_fetch import fetch_and_extract, merge_snippet_and_raw, needs_fetch
from strategic_research_agent.tools.relevance import refine_search_query, score_content_relevance
from strategic_research_agent.tools.tavily_search import tavily_search

logger = logging.getLogger(__name__)


class WebDeepState(TypedDict, total=False):
    user_query: str
    focus: str | None
    iteration: int
    refined_query: str
    search_results: list[dict[str, Any]]
    candidates: list[dict[str, Any]]
    scored: list[dict[str, Any]]
    accepted: list[dict[str, Any]]
    next_step: str


def _prepare(state: WebDeepState) -> dict[str, Any]:
    uq = (state.get("user_query") or "").strip()
    focus = (state.get("focus") or "").strip()
    rq = f"{uq} {focus}".strip() if focus else uq
    return {
        "refined_query": rq,
        "iteration": 0,
        "search_results": [],
        "candidates": [],
        "scored": [],
        "accepted": [],
        "next_step": "",
    }


def _search(state: WebDeepState) -> dict[str, Any]:
    q = (state.get("refined_query") or state.get("user_query") or "").strip()
    n = max(3, int(settings.deep_web_urls_per_iteration))
    rows = tavily_search(
        q,
        max_results=n,
        include_domains=None,
        include_raw_content=True,
    )
    return {"search_results": rows}


async def _enrich(state: WebDeepState) -> dict[str, Any]:
    rows = list(state.get("search_results") or [])
    max_chars = int(settings.deep_web_max_content_chars)
    candidates: list[dict[str, Any]] = []

    async def one(row: dict[str, Any]) -> dict[str, Any]:
        url = str(row.get("url") or "").strip()
        title = str(row.get("title") or "")
        base = merge_snippet_and_raw(row)
        source = "tavily"
        if needs_fetch(row) and url:
            got = await asyncio.to_thread(fetch_and_extract, url)
            if got.get("ok") and (got.get("text") or ""):
                base = str(got["text"])
                source = "extracted"
                if got.get("title"):
                    title = str(got["title"]) or title
        text = (base or "")[:max_chars]
        return {
            "url": url,
            "title": title,
            "text": text,
            "source": source,
            "tavily_score": row.get("tavily_score"),
        }

    limit = max(3, int(settings.deep_web_urls_per_iteration))
    tasks = [one(r) for r in rows[:limit]]
    if not tasks:
        return {"candidates": []}
    merged = await asyncio.gather(*tasks)
    candidates.extend(merged)
    return {"candidates": candidates}


async def _score(state: WebDeepState) -> dict[str, Any]:
    uq = (state.get("user_query") or "").strip()
    cands = list(state.get("candidates") or [])
    scored: list[dict[str, Any]] = []

    async def score_one(c: dict[str, Any]) -> dict[str, Any]:
        rel = await score_content_relevance(uq, c.get("title") or "", c.get("text") or "")
        return {**c, **rel}

    if not cands:
        return {"scored": []}
    scored = await asyncio.gather(*[score_one(c) for c in cands])
    return {"scored": list(scored)}


def _decide(state: WebDeepState) -> dict[str, Any]:
    scored = sorted(
        list(state.get("scored") or []),
        key=lambda x: float(x.get("score") or 0.0),
        reverse=True,
    )
    thr = float(settings.deep_web_min_relevance)
    good = float(settings.deep_web_good_enough)
    min_acc = max(1, int(settings.deep_web_min_accepted))
    max_iter = max(1, int(settings.deep_web_max_iterations))
    it = int(state.get("iteration") or 0)

    accepted_rows: list[dict[str, Any]] = []
    max_c = int(settings.deep_web_max_content_chars)
    for s in scored:
        if float(s.get("score") or 0.0) >= thr:
            accepted_rows.append(
                {
                    "kind": "web",
                    "title": s.get("title") or "",
                    "url": s.get("url") or "",
                    "content": (s.get("text") or "")[:max_c],
                    "source": "tavily_deep",
                    "deep_web": True,
                    "relevance_score": s.get("score"),
                    "relevance_reason": s.get("reason"),
                    "content_source": s.get("source"),
                }
            )

    best = float(scored[0].get("score") or 0.0) if scored else 0.0
    enough = (len(accepted_rows) >= min_acc) or (best >= good and len(accepted_rows) >= 1)

    if enough or it + 1 >= max_iter:
        if not accepted_rows and scored:
            for s in scored[:3]:
                accepted_rows.append(
                    {
                        "kind": "web",
                        "title": s.get("title") or "",
                        "url": s.get("url") or "",
                        "content": (s.get("text") or "")[:max_c],
                        "source": "tavily_deep",
                        "deep_web": True,
                        "relevance_score": s.get("score"),
                        "relevance_reason": s.get("reason") or "fallback_top",
                        "content_source": s.get("source"),
                    }
                )
        return {"accepted": accepted_rows, "next_step": "end"}

    return {"accepted": [], "next_step": "refine", "iteration": it + 1}


async def _refine(state: WebDeepState) -> dict[str, Any]:
    uq = (state.get("user_query") or "").strip()
    prev = (state.get("refined_query") or uq).strip()
    it = int(state.get("iteration") or 1)
    nq = await refine_search_query(uq, prev, it)
    return {"refined_query": nq, "search_results": [], "candidates": [], "scored": []}


def _route_decide(state: WebDeepState) -> str:
    return "refine" if state.get("next_step") == "refine" else "end"


def build_web_deep_graph():
    g = StateGraph(WebDeepState)
    g.add_node("prepare", _prepare)
    g.add_node("search", _search)
    g.add_node("enrich", _enrich)
    g.add_node("score", _score)
    g.add_node("decide", _decide)
    g.add_node("refine", _refine)

    g.set_entry_point("prepare")
    g.add_edge("prepare", "search")
    g.add_edge("search", "enrich")
    g.add_edge("enrich", "score")
    g.add_edge("score", "decide")
    g.add_conditional_edges(
        "decide",
        _route_decide,
        {"refine": "refine", "end": END},
    )
    g.add_edge("refine", "search")
    return g.compile()


_compiled = None


def _graph():
    global _compiled
    if _compiled is None:
        _compiled = build_web_deep_graph()
    return _compiled


async def run_web_deep_research(user_query: str, focus: str | None = None) -> list[dict[str, Any]]:
    """Run deep web pipeline; returns evidence rows (``kind=web``)."""
    q = (user_query or "").strip()
    if not q:
        return [{"kind": "error", "tool": "deep_web_research", "message": "empty query"}]

    initial: WebDeepState = {"user_query": q, "focus": (focus or "").strip() or None}
    try:
        out = await _graph().ainvoke(initial, config={"recursion_limit": 30})
    except Exception as e:
        logger.exception("web_deep graph failed: %s", e)
        return [{"kind": "error", "tool": "deep_web_research", "message": str(e)}]

    rows = list(out.get("accepted") or [])
    logger.info("web_deep: iterations_used=%s accepted=%s", out.get("iteration"), len(rows))
    return rows
