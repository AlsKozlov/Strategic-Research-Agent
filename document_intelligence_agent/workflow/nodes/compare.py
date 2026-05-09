"""Task 4 — Document Comparison node."""

from __future__ import annotations

import json
import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)


def _heuristic_compare(documents: list[str]) -> dict[str, Any]:
    if len(documents) < 2:
        return {
            "pairs": [],
            "confidence": "low",
            "gaps": ["Need at least 2 documents to compare."],
            "evidence": [],
        }
    # Simple word-set diff as fallback
    pairs = []
    for i in range(len(documents) - 1):
        words_a = set(documents[i].lower().split())
        words_b = set(documents[i + 1].lower().split())
        added = list(words_b - words_a)[:20]
        removed = list(words_a - words_b)[:20]
        pairs.append({
            "doc_a": i,
            "doc_b": i + 1,
            "added_tokens": added,
            "removed_tokens": removed,
            "changed": [],
            "contradicted": [],
        })
    return {
        "pairs": pairs,
        "confidence": "low",
        "gaps": ["Set DIA_OPENAI_API_KEY for semantic comparison."],
        "evidence": [],
    }


async def _llm_compare(request: str, documents: list[str]) -> dict[str, Any]:
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    doc_block = "\n\n".join(
        f"<document index=\"{i + 1}\">\n{doc[:5000]}\n</document>"
        for i, doc in enumerate(documents[:6])
    )
    system = (
        "You are a document comparison specialist. "
        "Compare all provided documents and identify differences.\n"
        "For each pair (or across all docs) produce:\n"
        "  - added: content present in the newer doc but not the older\n"
        "  - removed: content present in the older doc but not the newer\n"
        "  - changed: content that exists in both but was modified\n"
        "  - contradicted: statements that directly contradict each other\n\n"
        "Return JSON:\n"
        '{"pairs": [{"doc_a": 0, "doc_b": 1, "added": [...], "removed": [...], '
        '"changed": [...], "contradicted": [...]}], '
        '"overall_confidence": "high|medium|low", "gaps": [...]}'
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
        pairs = data.get("pairs") or []
        evidence = []
        for pair in pairs:
            for item in (pair.get("contradicted") or [])[:3]:
                evidence.append({"doc_idx": pair.get("doc_a", 0), "quote": str(item)[:200]})
        return {
            "pairs": pairs,
            "confidence": str(data.get("overall_confidence") or "medium"),
            "gaps": [str(g) for g in (data.get("gaps") or [])],
            "evidence": evidence,
        }
    except Exception:
        logger.warning("compare JSON parse failed")
        return {"pairs": [], "confidence": "low", "gaps": ["LLM parse error."], "evidence": []}


async def compare_node(state: DocIntelState) -> dict[str, Any]:
    request = state.get("request") or ""
    documents = state.get("documents") or []

    if len(documents) < 2:
        return {"task_result": {"pairs": [], "confidence": "low", "gaps": ["Provide at least 2 documents to compare."], "evidence": []}}

    if not settings.openai_api_key:
        return {"task_result": _heuristic_compare(documents)}

    result = await _llm_compare(request, documents)
    logger.info("compare: pairs=%d confidence=%s", len(result.get("pairs") or []), result.get("confidence"))
    return {"task_result": result}
