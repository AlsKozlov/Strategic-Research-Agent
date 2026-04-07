"""Processing engine: safety check, timeout wrapper, state → result mapping."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.governance.safety import looks_suspicious
from document_intelligence_agent.workflow.graph import run_doc_intel_graph

logger = logging.getLogger(__name__)


@dataclass
class DocIntelResult:
    task_type: str
    task_result: dict[str, Any]
    confidence: str
    evidence: list[dict[str, Any]]
    gaps: list[str]
    errors: list[str]
    latency_sec: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def _state_to_result(state: dict[str, Any]) -> DocIntelResult:
    return DocIntelResult(
        task_type=str(state.get("task_type") or "unknown"),
        task_result=dict(state.get("task_result") or {}),
        confidence=str(state.get("confidence") or "low"),
        evidence=list(state.get("evidence") or []),
        gaps=list(state.get("gaps") or []),
        errors=list(state.get("errors") or []),
        latency_sec=float(state.get("_latency_sec") or 0.0),
        metadata={"architecture": "classify→dispatch→finalize+LangGraph"},
    )


def _rejected(request: str, t0: float, reason: str) -> DocIntelResult:
    return DocIntelResult(
        task_type="unknown",
        task_result={},
        confidence="N/A",
        evidence=[],
        gaps=[reason],
        errors=[reason],
        latency_sec=time.perf_counter() - t0,
        metadata={"rejected": True},
    )


from document_intelligence_agent.observability.langfuse_client import observe


@observe(name="run_doc_intel")
async def run_doc_intel(
    request: str,
    documents: list[str],
    doc_meta: list[dict[str, Any]] | None = None,
    output_schema: dict[str, Any] | None = None,
    target_format: str | None = None,
    summary_format: str | None = None,
) -> DocIntelResult:
    t0 = time.perf_counter()

    # Safety: defence-in-depth — A2A boundary already checks, but we re-check
    # here so direct callers (CLI, tests) still get the same protection.
    if settings.safety_enabled and looks_suspicious(request):
        return _rejected(request, t0, "Request rejected by safety heuristics.")

    # Clamp document count and size first, then scan each document body
    truncated = [
        i for i, d in enumerate(documents[: settings.max_documents])
        if len(d) > settings.max_document_chars
    ]
    if truncated:
        logger.warning(
            "doc_intel: truncated %d document(s) to max_document_chars=%d",
            len(truncated),
            settings.max_document_chars,
        )
    if len(documents) > settings.max_documents:
        logger.warning(
            "doc_intel: dropped %d document(s) over max_documents=%d",
            len(documents) - settings.max_documents,
            settings.max_documents,
        )
    documents = [d[: settings.max_document_chars] for d in documents[: settings.max_documents]]

    from document_intelligence_agent.governance.safety import document_has_injection

    injected = [i for i, d in enumerate(documents) if document_has_injection(d)]
    if injected:
        return _rejected(
            request,
            t0,
            f"Document(s) at index {injected} contain prompt-injection patterns and were rejected.",
        )

    try:
        state = await asyncio.wait_for(
            run_doc_intel_graph(
                request=request,
                documents=documents,
                doc_meta=doc_meta,
                output_schema=output_schema,
                target_format=target_format,
                summary_format=summary_format,
            ),
            timeout=float(settings.processing_timeout_sec),
        )
    except asyncio.TimeoutError:
        logger.warning("doc_intel timed out after %ss", settings.processing_timeout_sec)
        return _rejected(
            request,
            t0,
            f"Timed out after {settings.processing_timeout_sec}s. Try a shorter document or raise DIA_PROCESSING_TIMEOUT_SEC.",
        )
    except Exception as exc:
        logger.exception("doc_intel graph failed: %s", exc)
        return _rejected(request, t0, f"Internal error: {exc}")

    result = _state_to_result(state)
    if result.latency_sec <= 0:
        result.latency_sec = time.perf_counter() - t0
    return result
