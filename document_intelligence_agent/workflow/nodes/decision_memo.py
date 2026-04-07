"""Task 6 — Decision Memo Generation node."""

from __future__ import annotations

import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)

_MEMO_SECTIONS = ["context", "options", "analysis", "risks", "recommendation"]


def _heuristic_memo(documents: list[str]) -> dict[str, Any]:
    combined = " ".join(doc[:300] for doc in documents)
    return {
        "memo": {
            "context": combined[:500],
            "options": [],
            "analysis": "",
            "risks": [],
            "recommendation": "",
        },
        "confidence": "low",
        "gaps": ["Set DIA_OPENAI_API_KEY for structured decision memo generation."],
        "evidence": [],
    }


async def _llm_decision_memo(request: str, documents: list[str]) -> dict[str, Any]:
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    doc_block = "\n\n".join(
        f"<document index=\"{i + 1}\">\n{doc[:5000]}\n</document>"
        for i, doc in enumerate(documents)
    )
    system = (
        "You are a strategic analyst. Produce a structured decision memo as a ready-to-use one-pager.\n"
        "The memo must include these sections:\n"
        "  context        — background and why a decision is needed\n"
        "  options        — list of alternatives (each with pros and cons)\n"
        "  analysis       — comparative evaluation of options\n"
        "  risks          — key risks and mitigations for the recommended option\n"
        "  recommendation — clear, actionable recommendation with rationale\n\n"
        "Cite document indices where relevant.\n"
        "End with:\n"
        "  Confidence: high | medium | low\n"
        "  Gaps: bullet list of missing information needed for a better decision"
    )
    user = f"Request: {request}\n\nDocuments:\n{doc_block}"
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
        max_tokens=3000,
    )
    text = (resp.choices[0].message.content or "").strip()

    # Parse sections heuristically from the response
    memo: dict[str, Any] = {s: "" for s in _MEMO_SECTIONS}
    confidence = "medium"
    gaps: list[str] = []
    current_section: str | None = None
    section_lines: dict[str, list[str]] = {s: [] for s in _MEMO_SECTIONS}

    for line in text.splitlines():
        ll = line.strip().lower()
        if ll.startswith("confidence:"):
            val = line.split(":", 1)[-1].strip().lower()
            if val in ("high", "medium", "low"):
                confidence = val
            continue
        if ll.startswith("gaps:"):
            current_section = "gaps"
            continue
        matched = False
        for sec in _MEMO_SECTIONS:
            if ll.startswith(sec + ":") or ll.startswith(f"## {sec}") or ll.startswith(f"**{sec}"):
                current_section = sec
                matched = True
                break
        if matched:
            continue
        if current_section == "gaps" and line.strip().startswith("-"):
            gaps.append(line.strip().lstrip("- ").strip())
        elif current_section in _MEMO_SECTIONS:
            section_lines[current_section].append(line)

    for sec in _MEMO_SECTIONS:
        memo[sec] = "\n".join(section_lines[sec]).strip() or ""

    # If parsing failed, store raw text under context
    if not any(memo.values()):
        memo["context"] = text

    evidence = [{"doc_idx": i, "quote": doc.strip()[:150]} for i, doc in enumerate(documents[:3])]
    return {
        "memo": memo,
        "confidence": confidence,
        "gaps": gaps,
        "evidence": evidence,
    }


async def decision_memo_node(state: DocIntelState) -> dict[str, Any]:
    request = state.get("request") or ""
    documents = state.get("documents") or []

    if not documents:
        return {"task_result": {"memo": {s: "" for s in _MEMO_SECTIONS}, "confidence": "low", "gaps": ["No documents provided."], "evidence": []}}

    if not settings.openai_api_key:
        return {"task_result": _heuristic_memo(documents)}

    result = await _llm_decision_memo(request, documents)
    logger.info("decision_memo: confidence=%s", result.get("confidence"))
    return {"task_result": result}
