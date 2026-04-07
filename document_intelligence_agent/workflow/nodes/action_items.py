"""Task 5 — Action Item Extraction node."""

from __future__ import annotations

import json
import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)


def _heuristic_action_items(documents: list[str]) -> dict[str, Any]:
    import re

    items: list[dict[str, Any]] = []
    # Look for lines containing action verbs
    action_verbs = re.compile(
        r"\b(will|must|shall|should|needs? to|has to|action:|todo:|follow.?up|assign|responsible|owner)\b",
        re.I,
    )
    for doc_idx, doc in enumerate(documents):
        for line in doc.splitlines():
            if action_verbs.search(line) and len(line.strip()) > 10:
                items.append({
                    "action": line.strip()[:300],
                    "owner": None,
                    "deadline": None,
                    "dependencies": [],
                    "doc_idx": doc_idx,
                    "confidence": "low",
                })
    return {
        "action_items": items[:30],
        "confidence": "low",
        "gaps": ["Set DIA_OPENAI_API_KEY for full action item extraction."],
        "evidence": [{"doc_idx": it["doc_idx"], "quote": it["action"][:150]} for it in items[:10]],
    }


async def _llm_action_items(request: str, documents: list[str]) -> dict[str, Any]:
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    doc_block = "\n\n".join(
        f"<document index=\"{i + 1}\">\n{doc[:6000]}\n</document>"
        for i, doc in enumerate(documents)
    )
    system = (
        "You are an action item extraction specialist. "
        "Extract every task, commitment, and follow-up from the documents.\n"
        "For each action item:\n"
        "  - action: clear description of what needs to be done\n"
        "  - owner: person or team responsible (null if not stated)\n"
        "  - deadline: due date or timeframe (null if not stated)\n"
        "  - dependencies: list of blockers or prerequisites\n"
        "  - doc_idx: 0-based document index where this was found\n"
        "  - confidence: high | medium | low\n\n"
        "Return JSON:\n"
        '{"action_items": [{...}], "overall_confidence": "high|medium|low", "gaps": [...]}'
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
        items = data.get("action_items") or []
        evidence = [
            {"doc_idx": it.get("doc_idx", 0), "quote": str(it.get("action") or "")[:200]}
            for it in items[:15]
        ]
        return {
            "action_items": items,
            "confidence": str(data.get("overall_confidence") or "medium"),
            "gaps": [str(g) for g in (data.get("gaps") or [])],
            "evidence": evidence,
        }
    except Exception:
        logger.warning("action_items JSON parse failed")
        return {"action_items": [], "confidence": "low", "gaps": ["LLM parse error."], "evidence": []}


async def action_items_node(state: DocIntelState) -> dict[str, Any]:
    request = state.get("request") or ""
    documents = state.get("documents") or []

    if not documents:
        return {"task_result": {"action_items": [], "confidence": "low", "gaps": ["No documents provided."], "evidence": []}}

    if not settings.openai_api_key:
        return {"task_result": _heuristic_action_items(documents)}

    result = await _llm_action_items(request, documents)
    logger.info("action_items: items=%d confidence=%s", len(result.get("action_items") or []), result.get("confidence"))
    return {"task_result": result}
