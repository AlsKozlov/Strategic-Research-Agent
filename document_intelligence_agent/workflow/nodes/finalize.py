"""Finalize node: add confidence + evidence attribution envelope.

Also handles the standalone confidence_attr task (task 10).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)


def _auto_evidence(documents: list[str], task_result: dict) -> list[dict[str, Any]]:
    """Return evidence from task_result, or auto-sample from docs."""
    ev = task_result.get("evidence")
    if ev:
        return list(ev)
    return [
        {"doc_idx": i, "quote": doc.strip()[:150]}
        for i, doc in enumerate(documents[:5])
        if doc.strip()
    ]


async def _llm_confidence_attr(
    request: str,
    documents: list[str],
) -> dict[str, Any]:
    """Standalone task 10: annotate every claim in the docs with confidence."""
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    doc_block = "\n\n".join(
        f"<document index=\"{i + 1}\">\n{doc[:4000]}\n</document>"
        for i, doc in enumerate(documents[:5])
    )
    system = (
        "You are an evidence attribution analyst. "
        "Extract all key claims from the documents and for each claim provide:\n"
        "  - claim: the statement being made\n"
        "  - confidence: high | medium | low | unknown\n"
        "  - source_doc: 1-based document index\n"
        "  - quote: the exact supporting excerpt from the document\n"
        "  - gaps: any uncertainty, missing evidence, or why confidence is limited\n\n"
        "Return JSON:\n"
        '{"claims": [{...}], "overall_confidence": "high|medium|low", "gaps": [...]}'
    )
    user = f"Request: {request}\n\nDocuments:\n{doc_block}"
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=2500,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
        claims = data.get("claims") or []
        evidence = [
            {
                "doc_idx": c.get("source_doc", 1) - 1,
                "quote": str(c.get("quote") or "")[:200],
                "confidence": str(c.get("confidence") or "unknown"),
            }
            for c in claims
        ]
        return {
            "claims": claims,
            "overall_confidence": str(data.get("overall_confidence") or "medium"),
            "gaps": [str(g) for g in (data.get("gaps") or [])],
            "evidence": evidence,
        }
    except Exception:
        logger.warning("confidence_attr JSON parse failed")
        return {"claims": [], "overall_confidence": "low", "gaps": ["LLM parse error."], "evidence": []}


async def finalize_node(state: DocIntelState) -> dict[str, Any]:
    task_type = state.get("task_type") or "unknown"
    documents = state.get("documents") or []
    task_result = state.get("task_result") or {}
    request = state.get("request") or ""
    errors = state.get("errors") or []

    # ── Standalone confidence_attr task ─────────────────────────────────────
    if task_type == "confidence_attr":
        if settings.openai_api_key and documents:
            attr = await _llm_confidence_attr(request, documents)
            confidence = attr.get("overall_confidence") or "medium"
            evidence = attr.get("evidence") or []
            gaps = attr.get("gaps") or []
            if errors:
                gaps += [f"Error: {e}" for e in errors]
            logger.info("finalize(confidence_attr): claims=%d confidence=%s", len(attr.get("claims") or []), confidence)
            return {
                "task_result": {"claims": attr.get("claims") or []},
                "confidence": confidence,
                "evidence": evidence,
                "gaps": gaps,
            }
        return {
            "task_result": {"claims": []},
            "confidence": "low",
            "evidence": [],
            "gaps": ["Set DIA_OPENAI_API_KEY for confidence attribution."],
        }

    # ── Standard: wrap task_result with the final envelope ──────────────────
    confidence = str(task_result.get("confidence") or "medium")
    gaps = [str(g) for g in (task_result.get("gaps") or [])]
    if errors:
        gaps += [f"Error: {e}" for e in errors]
    evidence = _auto_evidence(documents, task_result)

    logger.info(
        "finalize: task=%s confidence=%s evidence=%d gaps=%d",
        task_type, confidence, len(evidence), len(gaps),
    )
    return {
        "confidence": confidence,
        "evidence": evidence,
        "gaps": gaps,
    }
