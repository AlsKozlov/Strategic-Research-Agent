"""Classify node: determine task type from user request."""

from __future__ import annotations

import json
import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)

TASK_TYPES = [
    "summarize",
    "fact_extract",
    "structured_extract",
    "compare",
    "action_items",
    "decision_memo",
    "template_map",
    "multi_synthesis",
    "conflict_detect",
    "confidence_attr",
]

_HINTS: dict[str, list[str]] = {
    "summarize": ["summar", "condense", "brief", "overview", "tldr", "digest", "shorten"],
    "fact_extract": ["fact", "figure", "kpi", "number", "date", "obligation", "claim", "statistic"],
    "structured_extract": ["json", "table", "schema", "struct", "field", "extract to", "fill", "spreadsheet"],
    "compare": ["compar", "diff", "difference", "versus", " vs ", "contrast", "change between", "version"],
    "action_items": ["action item", "todo", "task", "follow-up", "who", "next step", "assignment", "responsible"],
    "decision_memo": ["decision", "memo", "option", "recommend", "one-pager", "trade-off", "analysis"],
    "template_map": ["convert", "transform", "reformat", "map to", "turn into", "notes to", "transcript to", "format"],
    "multi_synthesis": ["synthesize", "combine", "merge", "unify", "reconcile", "aggregate", "consolidate"],
    "conflict_detect": ["conflict", "contradict", "inconsisten", "discrepan", "mismatch", "clash"],
    "confidence_attr": ["confidence", "evidence", "attribution", "reliable", "verify", "source", "annotate"],
}


def heuristic_classify(request: str, n_docs: int) -> str:
    lower = request.lower()
    scores: dict[str, int] = {t: 0 for t in TASK_TYPES}
    for task, hints in _HINTS.items():
        for h in hints:
            if h in lower:
                scores[task] += 1
    best = max(scores, key=lambda t: scores[t])
    if scores[best] == 0:
        # Default based on doc count
        return "multi_synthesis" if n_docs >= 3 else "summarize"
    return best


async def llm_classify(request: str, n_docs: int) -> str:
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    system = (
        "You are the task classifier for Document Intelligence Agent. "
        "Given a user request and document count, pick ONE task type.\n"
        f"Valid types: {', '.join(TASK_TYPES)}\n\n"
        "Definitions:\n"
        "  summarize          — condense doc(s) into a structured summary\n"
        "  fact_extract       — extract verifiable facts, numbers, dates, KPIs\n"
        "  structured_extract — convert text to JSON/table following a schema\n"
        "  compare            — diff two+ documents (added/removed/changed)\n"
        "  action_items       — extract who does what by when\n"
        "  decision_memo      — produce context/options/risks/recommendation\n"
        "  template_map       — transform format (notes→PRD, transcript→report)\n"
        "  multi_synthesis    — combine multiple docs into unified narrative\n"
        "  conflict_detect    — find contradictions across documents\n"
        "  confidence_attr    — annotate claims with source and confidence\n\n"
        'Return JSON: {"task_type": "<one of the above>"}'
    )
    user = f"Request: {request}\nDocument count: {n_docs}"
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
        tt = str(data.get("task_type") or "").strip()
        if tt in TASK_TYPES:
            return tt
    except Exception:
        pass
    logger.warning("llm_classify parse failed; falling back to heuristic")
    return heuristic_classify(request, n_docs)


async def classify_node(state: DocIntelState) -> dict[str, Any]:
    request = state.get("request") or ""
    docs = state.get("documents") or []

    if settings.openai_api_key:
        task_type = await llm_classify(request, len(docs))
    else:
        task_type = heuristic_classify(request, len(docs))

    logger.info("classify: task_type=%s docs=%d", task_type, len(docs))
    return {"task_type": task_type}


def route_by_task(state: DocIntelState) -> str:
    """Conditional edge: route to the appropriate task node."""
    task = state.get("task_type") or "summarize"
    # confidence_attr goes directly to finalize (finalize IS the task)
    if task == "confidence_attr":
        return "finalize"
    if task not in TASK_TYPES:
        return "summarize"
    return task
