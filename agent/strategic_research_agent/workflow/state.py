from __future__ import annotations

from typing import TypedDict


class ResearchState(TypedDict, total=False):
    """Graph state for PAR + synthesis."""

    query: str
    kb_context: list[str]

    task_type: str
    plan_steps: list[str]
    use_tavily: bool
    use_arxiv: bool
    use_aggregator_scoped_tavily: bool
    tavily_queries: list[str]
    arxiv_queries: list[str]
    aggregator_domains: list[str]

    evidence: list[dict]
    tools_used: list[str]

    act_count: int
    needs_more: bool
    pending_tavily_queries: list[str]
    pending_arxiv_queries: list[str]
    reflection_notes: str

    report_markdown: str
    confidence: str
    caveats: list[str]
    errors: list[str]
