"""Task 1 — Summarization node."""

from __future__ import annotations

import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)

_FORMAT_INSTRUCTIONS = {
    "executive": "Write a 3–5 sentence executive summary highlighting purpose, key outcomes, and impact.",
    "bullets": "Write a bulleted list of the most important points (max 10 bullets).",
    "risks": "Focus on risks, issues, and open questions. Use a bulleted list.",
    "actions": "Focus on decisions made and actions required. Use a table: Action | Owner | Deadline.",
    "detailed": "Write a comprehensive summary covering all major sections and details.",
}
_DEFAULT_FORMAT = "bullets"


def _heuristic_summary(documents: list[str], fmt: str) -> dict[str, Any]:
    lines = []
    for i, doc in enumerate(documents):
        snippet = doc.strip()[:500]
        lines.append(f"Document {i + 1}: {snippet}...")
    return {
        "format": fmt,
        "summary": "\n\n".join(lines),
        "confidence": "low",
        "gaps": ["Set DIA_OPENAI_API_KEY for full summarization."],
        "evidence": [],
    }


async def _llm_summarize(
    request: str,
    documents: list[str],
    fmt: str,
) -> dict[str, Any]:
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    fmt_instr = _FORMAT_INSTRUCTIONS.get(fmt, _FORMAT_INSTRUCTIONS[_DEFAULT_FORMAT])
    doc_block = "\n\n".join(
        f"<document index=\"{i + 1}\">\n{doc[:8000]}\n</document>"
        for i, doc in enumerate(documents)
    )
    system = (
        "You are a professional document summarizer. "
        f"Format instruction: {fmt_instr}\n"
        "After the summary, add:\n"
        '  Confidence: high | medium | low\n'
        '  Gaps: bullet list of missing or uncertain information (or "None")\n'
        "Cite document numbers where relevant (e.g. [Doc 2])."
    )
    user = f"User request: {request}\n\nDocuments:\n{doc_block}"
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=2048,
    )
    text = (resp.choices[0].message.content or "").strip()

    # Parse confidence and gaps from trailing lines
    confidence = "medium"
    gaps: list[str] = []
    lines = text.splitlines()
    summary_lines: list[str] = []
    in_gaps = False
    for line in lines:
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
            summary_lines.append(line)

    return {
        "format": fmt,
        "summary": "\n".join(summary_lines).strip(),
        "confidence": confidence,
        "gaps": gaps,
        "evidence": [],
    }


async def summarize_node(state: DocIntelState) -> dict[str, Any]:
    request = state.get("request") or ""
    documents = state.get("documents") or []
    fmt = state.get("summary_format") or _DEFAULT_FORMAT

    if not documents:
        return {"task_result": {"format": fmt, "summary": "", "confidence": "low", "gaps": ["No documents provided."], "evidence": []}}

    if not settings.openai_api_key:
        return {"task_result": _heuristic_summary(documents, fmt)}

    result = await _llm_summarize(request, documents, fmt)
    logger.info("summarize: format=%s confidence=%s", fmt, result.get("confidence"))
    return {"task_result": result}
