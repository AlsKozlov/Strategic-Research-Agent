"""Task 9 — Conflict Detection node."""

from __future__ import annotations

import json
import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)


def _heuristic_conflicts(documents: list[str]) -> dict[str, Any]:
    if len(documents) < 2:
        return {
            "conflicts": [],
            "confidence": "low",
            "gaps": ["Need at least 2 documents to detect conflicts."],
            "evidence": [],
        }
    return {
        "conflicts": [],
        "confidence": "low",
        "gaps": ["Set DIA_OPENAI_API_KEY for conflict detection."],
        "evidence": [],
    }


async def _check_pair(
    client: Any,
    request: str,
    doc_a_idx: int,
    doc_b_idx: int,
    doc_a: str,
    doc_b: str,
) -> list[dict[str, Any]]:
    """Check one pair of documents for conflicts. Returns list of conflict dicts."""
    system = (
        "You are a conflict detection specialist. "
        "Compare two documents and identify ANY contradictions, inconsistencies, or conflicts.\n"
        "A conflict is when Document A states X but Document B states not-X (or a different value).\n\n"
        "Return JSON:\n"
        '{"conflicts": [{"type": "number|date|claim|conclusion|other", '
        '"doc_a_statement": "...", "doc_b_statement": "...", '
        '"severity": "high|medium|low", "explanation": "..."}], '
        '"has_conflicts": true|false}'
    )
    user = (
        f"Request: {request}\n\n"
        f"<document_a index=\"{doc_a_idx + 1}\">\n{doc_a}\n</document_a>\n\n"
        f"<document_b index=\"{doc_b_idx + 1}\">\n{doc_b}\n</document_b>"
    )
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=1500,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
        conflicts = []
        for c in data.get("conflicts") or []:
            c["doc_a"] = doc_a_idx
            c["doc_b"] = doc_b_idx
            conflicts.append(c)
        return conflicts
    except Exception:
        logger.warning(
            "conflict_detect: JSON parse failed for pair (%d, %d), raw=%s",
            doc_a_idx, doc_b_idx, raw[:300],
        )
        return []


async def _llm_detect_conflicts(request: str, documents: list[str]) -> dict[str, Any]:
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    n = len(documents)

    # Build pairs within budget
    pairs: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((i, j))
            if len(pairs) >= settings.conflict_max_pairs:
                break
        if len(pairs) >= settings.conflict_max_pairs:
            break

    # Check all pairs in parallel
    raw_results = await asyncio.gather(
        *[
            _check_pair(client, request, a, b, documents[a][:4000], documents[b][:4000])
            for a, b in pairs
        ],
        return_exceptions=True,
    )

    all_conflicts: list[dict[str, Any]] = []
    for result in raw_results:
        if isinstance(result, Exception):
            logger.warning("conflict_detect: pair check raised %s", result)
        elif isinstance(result, list):
            all_conflicts.extend(result)

    evidence: list[dict[str, Any]] = [
        {"doc_idx": c["doc_a"], "quote": str(c.get("doc_a_statement") or "")[:200]}
        for c in all_conflicts[:20]
    ]

    n_high = sum(1 for c in all_conflicts if c.get("severity") == "high")
    if n_high > 0:
        confidence = "high"
    elif all_conflicts:
        confidence = "medium"
    else:
        confidence = "high"  # high confidence: no conflicts found

    gaps: list[str] = []
    total_pairs = n * (n - 1) // 2
    if len(pairs) < total_pairs:
        gaps.append(f"Only checked {len(pairs)} of {total_pairs} pairs due to budget limit (DIA_CONFLICT_MAX_PAIRS).")

    return {
        "conflicts": all_conflicts,
        "pairs_checked": len(pairs),
        "confidence": confidence,
        "gaps": gaps,
        "evidence": evidence,
    }


async def conflict_detect_node(state: DocIntelState) -> dict[str, Any]:
    request = state.get("request") or ""
    documents = state.get("documents") or []

    if len(documents) < 2:
        return {"task_result": {"conflicts": [], "pairs_checked": 0, "confidence": "low", "gaps": ["Provide at least 2 documents."], "evidence": []}}

    if not settings.openai_api_key:
        return {"task_result": _heuristic_conflicts(documents)}

    result = await _llm_detect_conflicts(request, documents)
    logger.info("conflict_detect: conflicts=%d pairs=%d", len(result.get("conflicts") or []), result.get("pairs_checked", 0))
    return {"task_result": result}
