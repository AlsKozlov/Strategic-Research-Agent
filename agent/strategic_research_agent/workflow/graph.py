from __future__ import annotations

import time
from typing import Any

from langgraph.graph import END, StateGraph

from strategic_research_agent.workflow.nodes import (
    act_node,
    plan_node,
    reflect_node,
    route_after_reflect,
    synthesize_node,
)
from strategic_research_agent.workflow.state import ResearchState


def build_research_graph():
    g = StateGraph(ResearchState)
    g.add_node("plan", plan_node)
    g.add_node("act", act_node)
    g.add_node("reflect", reflect_node)
    g.add_node("synthesize", synthesize_node)
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


async def run_research_graph(query: str, kb_context: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    initial: ResearchState = {
        "query": query,
        "kb_context": kb_context or [],
    }
    graph = _get_graph()
    out = await graph.ainvoke(
        initial,
        config={"recursion_limit": 25},
    )
    out = dict(out)
    out["_latency_sec"] = time.perf_counter() - t0
    return out
