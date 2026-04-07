"""Task 2 — Fact Extraction node."""

from __future__ import annotations

import json
import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)


def _heuristic_facts(documents: list[str]) -> dict[str, Any]:
    import re

    facts: list[dict[str, Any]] = []
    # Simple regex patterns for numbers, dates, percentages
    patterns = [
        ("number", r"\b\d[\d,]*\.?\d*\s*(?:million|billion|thousand|%)?\b"),
        ("date", r"\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b"),
    ]
    for doc_idx, doc in enumerate(documents):
        for ftype, pattern in patterns:
            for m in re.finditer(pattern, doc, re.I):
                start = max(0, m.start() - 60)
                end = min(len(doc), m.end() + 60)
                context = doc[start:end].replace("\n", " ").strip()
                facts.append({
                    "type": ftype,
                    "value": m.group(),
                    "context": context,
                    "doc_idx": doc_idx,
                    "confidence": "low",
                })
    return {
        "facts": facts[:50],
        "confidence": "low",
        "gaps": ["Set DIA_OPENAI_API_KEY for semantic fact extraction."],
        "evidence": [],
    }


async def _llm_fact_extract(request: str, documents: list[str]) -> dict[str, Any]:
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    doc_block = "\n\n".join(
        f"<document index=\"{i + 1}\">\n{doc[:6000]}\n</document>"
        for i, doc in enumerate(documents)
    )
    system = (
        "You are a fact extraction specialist. Extract all verifiable facts from the documents.\n"
        "For each fact include:\n"
        "  - type: number | date | kpi | obligation | claim | condition | other\n"
        "  - value: the exact extracted value or statement\n"
        "  - context: 1-sentence surrounding context\n"
        "  - doc_idx: 0-based document index\n"
        "  - confidence: high | medium | low\n\n"
        "Return JSON:\n"
        '{"facts": [{...}], "overall_confidence": "high|medium|low", "gaps": ["..."]}'
    )
    user = f"Request: {request}\n\nDocuments:\n{doc_block}"
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=3000,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
        return {
            "facts": data.get("facts") or [],
            "confidence": str(data.get("overall_confidence") or "medium"),
            "gaps": [str(g) for g in (data.get("gaps") or [])],
            "evidence": [
                {"doc_idx": f.get("doc_idx", 0), "quote": str(f.get("context") or "")}
                for f in (data.get("facts") or [])[:20]
            ],
        }
    except Exception:
        logger.warning("fact_extract JSON parse failed")
        return {"facts": [], "confidence": "low", "gaps": ["LLM parse error."], "evidence": []}


async def fact_extract_node(state: DocIntelState) -> dict[str, Any]:
    request = state.get("request") or ""
    documents = state.get("documents") or []

    if not documents:
        return {"task_result": {"facts": [], "confidence": "low", "gaps": ["No documents provided."], "evidence": []}}

    if not settings.openai_api_key:
        return {"task_result": _heuristic_facts(documents)}

    result = await _llm_fact_extract(request, documents)
    logger.info("fact_extract: facts=%d confidence=%s", len(result.get("facts") or []), result.get("confidence"))
    return {"task_result": result}
