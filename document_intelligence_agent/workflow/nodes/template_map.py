"""Task 7 — Template / Format Mapping node."""

from __future__ import annotations

import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)

_FORMAT_DESCRIPTIONS = {
    "prd": "Product Requirements Document with sections: Overview, Goals, User Stories, Requirements, Acceptance Criteria, Out of Scope",
    "presentation": "Presentation outline with slide titles and bullet points per slide",
    "report": "Formal report with Executive Summary, Background, Findings, Conclusions, Recommendations",
    "email": "Professional email with Subject, Greeting, Body paragraphs, Call to action, Sign-off",
    "faq": "FAQ format with Question/Answer pairs",
    "meeting_minutes": "Meeting minutes: Date, Attendees, Agenda, Discussion Points, Decisions, Action Items",
    "standup": "Daily standup format: Yesterday, Today, Blockers",
    "okr": "OKR format: Objectives and Key Results with measurable metrics",
}


def _detect_target_format(request: str, explicit: str | None) -> tuple[str, str]:
    if explicit:
        desc = _FORMAT_DESCRIPTIONS.get(explicit.lower(), f"format: {explicit}")
        return explicit, desc
    lower = request.lower()
    for fmt, desc in _FORMAT_DESCRIPTIONS.items():
        if fmt in lower or fmt.replace("_", " ") in lower:
            return fmt, desc
    return "report", _FORMAT_DESCRIPTIONS["report"]


def _heuristic_map(documents: list[str], target_fmt: str) -> dict[str, Any]:
    combined = "\n\n".join(doc[:800] for doc in documents)
    return {
        "target_format": target_fmt,
        "output": combined,
        "confidence": "low",
        "gaps": ["Set DIA_OPENAI_API_KEY for format mapping."],
        "evidence": [],
    }


async def _llm_template_map(
    request: str,
    documents: list[str],
    target_fmt: str,
    fmt_description: str,
) -> dict[str, Any]:
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    doc_block = "\n\n".join(
        f"<document index=\"{i + 1}\">\n{doc[:6000]}\n</document>"
        for i, doc in enumerate(documents)
    )
    system = (
        f"You are a professional document formatter. Transform the source content into the following format:\n"
        f"{fmt_description}\n\n"
        "Preserve all key information. Do not invent new facts. "
        "Adapt tone, structure, and language to fit the target format.\n\n"
        "After the output add:\n"
        "  Confidence: high | medium | low\n"
        "  Gaps: bullet list of missing information that would improve the output"
    )
    user = f"Request: {request}\n\nSource content:\n{doc_block}"
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
        max_tokens=3000,
    )
    text = (resp.choices[0].message.content or "").strip()

    confidence = "medium"
    gaps: list[str] = []
    output_lines: list[str] = []
    in_gaps = False
    for line in text.splitlines():
        ll = line.strip().lower()
        if ll.startswith("confidence:"):
            val = line.split(":", 1)[-1].strip().lower()
            if val in ("high", "medium", "low"):
                confidence = val
        elif ll.startswith("gaps:"):
            in_gaps = True
        elif in_gaps and line.strip().startswith("-"):
            gap = line.strip().lstrip("- ").strip()
            if gap.lower() != "none":
                gaps.append(gap)
        else:
            in_gaps = False
            output_lines.append(line)

    return {
        "target_format": target_fmt,
        "output": "\n".join(output_lines).strip(),
        "confidence": confidence,
        "gaps": gaps,
        "evidence": [{"doc_idx": i, "quote": doc.strip()[:100]} for i, doc in enumerate(documents[:3])],
    }


async def template_map_node(state: DocIntelState) -> dict[str, Any]:
    request = state.get("request") or ""
    documents = state.get("documents") or []
    explicit_format = state.get("target_format")

    if not documents:
        return {"task_result": {"target_format": explicit_format or "report", "output": "", "confidence": "low", "gaps": ["No documents provided."], "evidence": []}}

    target_fmt, fmt_description = _detect_target_format(request, explicit_format)

    if not settings.openai_api_key:
        return {"task_result": _heuristic_map(documents, target_fmt)}

    result = await _llm_template_map(request, documents, target_fmt, fmt_description)
    logger.info("template_map: target=%s confidence=%s", target_fmt, result.get("confidence"))
    return {"task_result": result}
