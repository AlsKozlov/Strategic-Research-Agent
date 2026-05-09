from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.governance.safety import looks_suspicious
from strategic_research_agent.workflow.graph import run_research_graph

logger = logging.getLogger(__name__)


def _dedupe_by_url(rows: list[dict[str, Any]], url_key: str = "url") -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        u = str(r.get(url_key) or "")
        if u and u in seen:
            continue
        if u:
            seen.add(u)
        out.append(r)
    return out


@dataclass
class WebHit:
    title: str
    url: str
    snippet: str


@dataclass
class ResearchResult:
    query: str
    research_plan: list[str]
    web_hits: list[WebHit]
    arxiv_hits: list[dict[str, Any]]
    kb_snippets: list[str]
    report_markdown: str
    confidence: str
    caveats: list[str]
    latency_sec: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def _dedupe_webhits(hits: list[WebHit]) -> list[WebHit]:
    seen: set[str] = set()
    out: list[WebHit] = []
    for h in hits:
        if h.url and h.url in seen:
            continue
        if h.url:
            seen.add(h.url)
        out.append(h)
    return out


def _state_to_result(state: dict[str, Any]) -> ResearchResult:
    q = str(state.get("query") or "")
    plan = list(state.get("plan_steps") or [])
    kb = list(state.get("kb_context") or [])
    evidence = list(state.get("evidence") or [])
    web_hits: list[WebHit] = []
    arxiv_hits: list[dict[str, Any]] = []
    for e in evidence:
        if e.get("kind") == "arxiv" or e.get("source") == "arxiv":
            if e.get("error"):
                continue
            arxiv_hits.append(
                {
                    "title": e.get("title"),
                    "url": e.get("url"),
                    "summary": (e.get("summary") or "")[:2000],
                    "published": e.get("published"),
                }
            )
            continue
        url = str(e.get("url") or "")
        if not url and not e.get("title"):
            continue
        web_hits.append(
            WebHit(
                title=str(e.get("title") or ""),
                url=url,
                snippet=str(e.get("content") or e.get("snippet") or ""),
            )
        )
    meta = {
        "architecture": "PAR+LangGraph",
        "task_type": state.get("task_type"),
        "tools_used": state.get("tools_used") or [],
        "act_count": state.get("act_count"),
        "reflection_notes": state.get("reflection_notes"),
        "aggregator_domains": state.get("aggregator_domains"),
        "evidence_count": len(evidence),
    }
    return ResearchResult(
        query=q,
        research_plan=plan,
        web_hits=_dedupe_webhits(web_hits),
        arxiv_hits=_dedupe_by_url(arxiv_hits, "url"),
        kb_snippets=kb,
        report_markdown=str(state.get("report_markdown") or ""),
        confidence=str(state.get("confidence") or "Medium"),
        caveats=list(state.get("caveats") or []),
        latency_sec=float(state.get("_latency_sec") or 0.0),
        metadata=meta,
    )


async def run_research(
    query: str,
    kb_context: list[str] | None = None,
) -> ResearchResult:
    t0 = time.perf_counter()
    kb_context = kb_context or []
    if looks_suspicious(query):
        return ResearchResult(
            query=query,
            research_plan=[],
            web_hits=[],
            arxiv_hits=[],
            kb_snippets=kb_context,
            report_markdown="Request rejected by safety heuristics (see governance).",
            confidence="N/A",
            caveats=["Input matched basic injection / abuse heuristics."],
            latency_sec=time.perf_counter() - t0,
            metadata={"rejected": True, "architecture": "PAR+LangGraph"},
        )

    try:
        state = await asyncio.wait_for(
            run_research_graph(query, kb_context),
            timeout=float(settings.research_timeout_sec),
        )
    except asyncio.TimeoutError:
        logger.warning("research timed out after %ss", settings.research_timeout_sec)
        return ResearchResult(
            query=query,
            research_plan=[],
            web_hits=[],
            arxiv_hits=[],
            kb_snippets=kb_context,
            report_markdown="Research timed out; narrow the question or raise SRA_RESEARCH_TIMEOUT_SEC.",
            confidence="N/A",
            caveats=[f"Timeout after {settings.research_timeout_sec}s"],
            latency_sec=time.perf_counter() - t0,
            metadata={"timeout": True, "architecture": "PAR+LangGraph"},
        )
    except Exception as e:
        logger.exception("research graph failed: %s", e)
        return ResearchResult(
            query=query,
            research_plan=[],
            web_hits=[],
            arxiv_hits=[],
            kb_snippets=kb_context,
            report_markdown=f"Research failed: {e}",
            confidence="N/A",
            caveats=["Internal error"],
            latency_sec=time.perf_counter() - t0,
            metadata={"error": str(e), "architecture": "PAR+LangGraph"},
        )

    result = _state_to_result(state)
    if result.latency_sec <= 0:
        result.latency_sec = time.perf_counter() - t0
    return result
