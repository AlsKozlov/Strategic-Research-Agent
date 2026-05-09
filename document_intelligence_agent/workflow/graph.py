"""LangGraph graph definition for Document Intelligence Agent.

Topology:
    START → classify → [route_by_task] → {task_node} → finalize → END

    confidence_attr goes directly to finalize (it IS the finalize task).
"""

from __future__ import annotations

import time
from typing import Any

from langgraph.graph import END, StateGraph

from document_intelligence_agent.workflow.nodes import (
    action_items_node,
    classify_node,
    compare_node,
    conflict_detect_node,
    decision_memo_node,
    fact_extract_node,
    finalize_node,
    multi_synthesis_node,
    route_by_task,
    structured_extract_node,
    summarize_node,
    template_map_node,
)
from document_intelligence_agent.workflow.state import DocIntelState

_TASK_NODES = [
    "summarize",
    "fact_extract",
    "structured_extract",
    "compare",
    "action_items",
    "decision_memo",
    "template_map",
    "multi_synthesis",
    "conflict_detect",
]


def build_doc_intel_graph():
    g = StateGraph(DocIntelState)

    # ── Nodes ────────────────────────────────────────────────────────────────
    g.add_node("classify", classify_node)
    g.add_node("summarize", summarize_node)
    g.add_node("fact_extract", fact_extract_node)
    g.add_node("structured_extract", structured_extract_node)
    g.add_node("compare", compare_node)
    g.add_node("action_items", action_items_node)
    g.add_node("decision_memo", decision_memo_node)
    g.add_node("template_map", template_map_node)
    g.add_node("multi_synthesis", multi_synthesis_node)
    g.add_node("conflict_detect", conflict_detect_node)
    g.add_node("finalize", finalize_node)

    # ── Entry ────────────────────────────────────────────────────────────────
    g.set_entry_point("classify")

    # ── Dispatch: classify → task node ──────────────────────────────────────
    g.add_conditional_edges(
        "classify",
        route_by_task,
        {
            # 9 task nodes + direct-to-finalize for confidence_attr
            "summarize": "summarize",
            "fact_extract": "fact_extract",
            "structured_extract": "structured_extract",
            "compare": "compare",
            "action_items": "action_items",
            "decision_memo": "decision_memo",
            "template_map": "template_map",
            "multi_synthesis": "multi_synthesis",
            "conflict_detect": "conflict_detect",
            "finalize": "finalize",
        },
    )

    # ── All task nodes → finalize ────────────────────────────────────────────
    for node_name in _TASK_NODES:
        g.add_edge(node_name, "finalize")

    # ── finalize → END ───────────────────────────────────────────────────────
    g.add_edge("finalize", END)

    return g.compile()


# Initialise eagerly at import time — avoids TOCTOU race under concurrent first requests.
_compiled = build_doc_intel_graph()


def _get_graph():
    return _compiled


async def run_doc_intel_graph(
    request: str,
    documents: list[str],
    doc_meta: list[dict] | None = None,
    output_schema: dict | None = None,
    target_format: str | None = None,
    summary_format: str | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    initial: DocIntelState = {
        "request": request,
        "documents": documents,
        "doc_meta": doc_meta or [{} for _ in documents],
        "output_schema": output_schema,
        "target_format": target_format,
        "summary_format": summary_format,
        "errors": [],
    }
    graph = _get_graph()

    from document_intelligence_agent.observability import metrics
    from document_intelligence_agent.observability.langfuse_client import (
        get_langchain_handler,
    )

    handler = get_langchain_handler(
        trace_name="document_intelligence",
        metadata={
            "request": (request or "")[:512],
            "n_documents": len(documents),
            "target_format": target_format,
        },
        tags=["document-intelligence-agent", "langgraph"],
    )
    callbacks = [handler] if handler is not None else []

    status = "completed"
    try:
        out = await graph.ainvoke(
            initial,
            config={"recursion_limit": 25, "callbacks": callbacks},
        )
    except Exception:
        status = "failed"
        raise
    finally:
        latency = time.perf_counter() - t0
        metrics.document_job_latency_seconds.observe(latency)
        metrics.document_jobs_total.labels(status=status).inc()
        metrics.documents_processed_total.inc(len(documents))

    out = dict(out)
    out["_latency_sec"] = time.perf_counter() - t0
    return out
