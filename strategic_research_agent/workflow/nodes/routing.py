"""Conditional routing after reflect (PAR loop)."""

from __future__ import annotations

from strategic_research_agent.workflow.nodes.common import max_act_passes
from strategic_research_agent.workflow.state import ResearchState


def route_after_reflect(state: ResearchState) -> str:
    if state.get("needs_more") and int(state.get("act_count") or 0) < max_act_passes():
        return "act"
    return "synthesize"
