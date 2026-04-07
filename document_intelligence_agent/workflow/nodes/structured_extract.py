"""Task 3 — Structured Data Extraction node (JSON / Table)."""

from __future__ import annotations

import json
import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)


def _heuristic_extract(documents: list[str], schema: dict | None) -> dict[str, Any]:
    # Return raw text split into records as a minimal fallback
    records = [{"doc_idx": i, "raw_text": doc[:500]} for i, doc in enumerate(documents)]
    return {
        "schema_used": schema or {},
        "records": records,
        "confidence": "low",
        "gaps": ["Set DIA_OPENAI_API_KEY for schema-guided extraction."],
        "evidence": [],
    }


async def _llm_structured_extract(
    request: str,
    documents: list[str],
    schema: dict | None,
) -> dict[str, Any]:
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    schema_block = json.dumps(schema, ensure_ascii=False, indent=2) if schema else "Infer appropriate fields from the document content."
    doc_block = "\n\n".join(
        f"<document index=\"{i + 1}\">\n{doc[:6000]}\n</document>"
        for i, doc in enumerate(documents)
    )
    system = (
        "You are a structured data extraction specialist.\n"
        f"Target schema / instructions:\n{schema_block}\n\n"
        "Extract data from each document following the schema. "
        "If a field is missing, use null. "
        "Return JSON:\n"
        '{"records": [{"doc_idx": 0, "fields": {...}}], '
        '"schema_inferred": {...}, '
        '"overall_confidence": "high|medium|low", '
        '"gaps": ["..."]}'
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
            "schema_used": schema or data.get("schema_inferred") or {},
            "records": data.get("records") or [],
            "confidence": str(data.get("overall_confidence") or "medium"),
            "gaps": [str(g) for g in (data.get("gaps") or [])],
            "evidence": [
                {"doc_idx": r.get("doc_idx", 0), "quote": json.dumps(r.get("fields") or {})[:200]}
                for r in (data.get("records") or [])[:10]
            ],
        }
    except Exception:
        logger.warning("structured_extract JSON parse failed")
        return {"schema_used": schema or {}, "records": [], "confidence": "low", "gaps": ["LLM parse error."], "evidence": []}


async def structured_extract_node(state: DocIntelState) -> dict[str, Any]:
    request = state.get("request") or ""
    documents = state.get("documents") or []
    schema = state.get("output_schema")

    if not documents:
        return {"task_result": {"schema_used": schema or {}, "records": [], "confidence": "low", "gaps": ["No documents provided."], "evidence": []}}

    if not settings.openai_api_key:
        return {"task_result": _heuristic_extract(documents, schema)}

    result = await _llm_structured_extract(request, documents, schema)
    logger.info("structured_extract: records=%d confidence=%s", len(result.get("records") or []), result.get("confidence"))
    return {"task_result": result}
