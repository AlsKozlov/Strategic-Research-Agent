from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from strategic_research_agent.clients.dia_client import (
    DIAClientError,
    DIAUnavailable,
    get_dia_client,
)
from strategic_research_agent.config import settings
from strategic_research_agent.governance.citations import (
    CitationReport,
    validate_citations,
)
from strategic_research_agent.governance.safety import looks_suspicious
from strategic_research_agent.observability.langfuse_client import observe
from strategic_research_agent.workflow.graph import run_research_graph
from strategic_research_agent.workflow.nodes.confidence import (
    ConfidenceReport,
    score_confidence,
)

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


_DIA_MIN_DOC_CHARS = 4000


async def _maybe_call_dia(
    query: str,
    state: dict[str, Any],
    result: "ResearchResult",
) -> None:
    """Best-effort DIA call on the longest fetched document, if any."""
    evidence = state.get("evidence") or []
    candidates = [
        e for e in evidence
        if isinstance(e, dict) and isinstance(e.get("raw_content"), str)
        and len(e["raw_content"]) >= _DIA_MIN_DOC_CHARS
    ]
    if not candidates:
        return
    candidates.sort(key=lambda e: len(e.get("raw_content") or ""), reverse=True)
    top = candidates[0]

    try:
        client = get_dia_client()
    except DIAUnavailable:
        return

    if not client.check_available():
        logger.info("dia bridge breaker open; skipping")
        return

    instruction = f"Extract key facts and produce a structured summary for: {query}"
    try:
        dia_result = await client.analyze_document(
            instruction=instruction,
            document=str(top["raw_content"]),
            task_hint="brief",
        )
    except DIAClientError as e:
        logger.warning("dia bridge call failed: %s", e)
        return

    result.metadata["dia_extraction"] = {
        "task_type": dia_result.task_type,
        "confidence": dia_result.confidence,
        "source_url": top.get("url"),
        "task_result": dia_result.task_result,
        "evidence_count": len(dia_result.evidence),
    }
    logger.info(
        "dia bridge: extracted %s from %s",
        dia_result.task_type,
        top.get("url"),
    )


def _state_to_result(state: dict[str, Any]) -> ResearchResult:
    q = str(state.get("query") or "")
    plan = list(state.get("plan_steps") or [])
    kb = list(state.get("kb_context") or [])
    evidence = list(state.get("evidence") or [])
    web_hits: list[WebHit] = []
    arxiv_hits: list[dict[str, Any]] = []
    for e in evidence:
        kind = e.get("kind")
        source = e.get("source") or ""
        if kind == "arxiv" or source == "arxiv":
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
                snippet=str(e.get("content") or e.get("summary") or e.get("snippet") or ""),
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
        "citation_report": state.get("citation_report"),
        "confidence_signals": state.get("confidence_signals"),
        "pii_redactions": state.get("pii_redactions"),
        "kb_retriever_top_k": state.get("kb_retriever_top_k"),
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


@observe(name="run_research")
async def run_research(
    query: str,
    kb_context: list[str] | None = None,
) -> ResearchResult:
    t0 = time.perf_counter()
    kb_context = kb_context or []
    if settings.safety_enabled and looks_suspicious(query):
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
            report_markdown="Research failed due to an internal error. Please retry or narrow the question.",
            confidence="N/A",
            caveats=["Internal error"],
            latency_sec=time.perf_counter() - t0,
            metadata={"error": str(e), "architecture": "PAR+LangGraph"},
        )

    result = _state_to_result(state)
    if result.latency_sec <= 0:
        result.latency_sec = time.perf_counter() - t0

    # ── Post-hoc citation validation ─────────────────────────────────────────
    citation_report: CitationReport | None = None
    if settings.citation_validation_enabled and result.report_markdown:
        evidence_for_check = list(state.get("evidence") or [])
        rewritten, citation_report = validate_citations(
            result.report_markdown,
            evidence_for_check,
            strict=settings.citation_strict_mode,
        )
        if settings.citation_strict_mode:
            result.report_markdown = rewritten
        result.metadata["citation_report"] = citation_report.to_dict()
        if citation_report.unsupported_urls:
            result.caveats.append(
                f"{len(citation_report.unsupported_urls)} cited URL(s) "
                f"not found in retrieved evidence (integrity "
                f"{citation_report.integrity_score:.2f})."
            )

    # ── Optional DIA bridge ──────────────────────────────────────────────────
    # If a long fetched document is available and DIA is configured, hand it
    # off for structured extraction. We attach the result as side metadata
    # rather than rewriting the markdown report — the caller decides what to
    # do with it. Failures are non-fatal; the bridge is opt-in.
    if settings.dia_a2a_base_url:
        await _maybe_call_dia(query, state, result)

    # ── Re-score confidence with the richer heuristic ────────────────────────
    integrity = citation_report.integrity_score if citation_report else 1.0
    conf: ConfidenceReport = score_confidence(
        list(state.get("evidence") or []),
        citation_integrity=integrity,
    )
    result.confidence = conf.label
    result.metadata["confidence_signals"] = conf.to_dict()
    if conf.rationale:
        result.caveats.extend(conf.rationale)

    return result
