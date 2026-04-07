from __future__ import annotations

import time
from typing import Any

from langgraph.graph import END, StateGraph

from strategic_research_agent.observability import metrics
from strategic_research_agent.observability.langfuse_client import (
    get_langchain_handler,
)
from strategic_research_agent.workflow.nodes import (
    act_node,
    plan_node,
    reflect_node,
    route_after_reflect,
    synthesize_node,
)
from strategic_research_agent.workflow.state import ResearchState


def _timed_node(name: str, fn):
    async def wrapper(state, *a, **kw):
        t0 = time.perf_counter()
        try:
            return await fn(state, *a, **kw)
        finally:
            metrics.node_duration_seconds.labels(node=name).observe(
                time.perf_counter() - t0
            )

    wrapper.__name__ = f"{name}_timed"
    return wrapper


def build_research_graph():
    g = StateGraph(ResearchState)
    g.add_node("plan", _timed_node("plan", plan_node))
    g.add_node("act", _timed_node("act", act_node))
    g.add_node("reflect", _timed_node("reflect", reflect_node))
    g.add_node("synthesize", _timed_node("synthesize", synthesize_node))
    g.set_entry_point("plan")
    g.add_edge("plan", "act")
    g.add_edge("act", "reflect")
    g.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {"act": "act", "synthesize": "synthesize"},
    )
    g.add_edge("synthesize", END)
    return g.compile()


_compiled = None


def _get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_research_graph()
    return _compiled


async def run_research_graph(
    query: str,
    kb_context: list[str] | None = None,
    *,
    trace_id: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    initial: ResearchState = {
        "query": query,
        "kb_context": kb_context or [],
    }
    graph = _get_graph()

    handler = get_langchain_handler(
        trace_name="strategic_research",
        user_id=user_id,
        session_id=session_id,
        metadata={
            "query": query[:512],
            "kb_chunks": len(kb_context or []),
            "trace_id": trace_id,
        },
        tags=["strategic-research-agent", "langgraph"],
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
        metrics.research_task_latency_seconds.observe(latency)
        metrics.research_tasks_total.labels(status=status).inc()

    out = dict(out)
    out["_latency_sec"] = time.perf_counter() - t0
    return out
