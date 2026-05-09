"""Act node: LLM chooses tools (Tavily / arXiv / scoped web) or heuristic fallback without API key."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.tools.arxiv import arxiv_search
from strategic_research_agent.tools.tavily_search import tavily_search
from strategic_research_agent.utils.dedupe import dedupe_evidence
from strategic_research_agent.workflow.nodes.tool_runner import run_tool_agent
from strategic_research_agent.workflow.state import ResearchState

logger = logging.getLogger(__name__)


async def collect_tavily(
    queries: list[str],
    include_domains: list[str] | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for q in queries:
        if not q.strip():
            continue
        rows = await asyncio.to_thread(tavily_search, q, settings.max_web_results, include_domains)
        for row in rows:
            key = (row.get("url") or "") + (row.get("title") or "")
            if key in seen:
                continue
            seen.add(key)
            out.append({"kind": "web", **row})
    return out


async def _heuristic_retrieval(state: ResearchState, act_count: int) -> tuple[list[dict[str, Any]], list[str]]:
    """No OpenAI key: run parallel Tavily + arXiv from plan hints."""
    q = state.get("query") or ""
    tools_used: list[str] = []
    tq: list[str]
    aq: list[str]
    if act_count == 1:
        tq = list(state.get("tavily_queries") or [q])
        aq = list(state.get("arxiv_queries") or [])
        if not aq and state.get("use_arxiv"):
            aq = [q]
    else:
        tq = list(state.get("pending_tavily_queries") or [])
        aq = list(state.get("pending_arxiv_queries") or [])

    use_tavily = bool(state.get("use_tavily", True))
    use_arxiv = bool(state.get("use_arxiv", True))
    use_agg = bool(state.get("use_aggregator_scoped_tavily", True))
    domains = list(state.get("aggregator_domains") or [])

    new_evidence: list[dict[str, Any]] = []

    tq_eff = tq if tq else [q]
    seed = (tq_eff[0] if tq_eff else q).strip() or q

    agg_task = None
    if use_tavily and use_agg and domains and act_count == 1:
        agg_task = collect_tavily([seed], domains)

    web_task = None
    if use_tavily:
        web_task = collect_tavily(tq_eff, None)

    if agg_task is not None and web_task is not None:
        agg_rows, web_rows = await asyncio.gather(agg_task, web_task)
        if agg_rows or web_rows:
            tools_used.append("tavily_search")
        new_evidence.extend(agg_rows or [])
        new_evidence.extend(web_rows or [])
    elif web_task is not None:
        web_rows = await web_task
        if web_rows:
            tools_used.append("tavily_search")
            new_evidence.extend(web_rows)
    elif agg_task is not None:
        agg_rows = await agg_task
        if agg_rows:
            tools_used.append("tavily_search")
            new_evidence.extend(agg_rows)

    if use_arxiv and aq:
        arxiv_tasks = [arxiv_search(aqry.strip(), settings.max_arxiv_results) for aqry in aq if aqry.strip()]
        if arxiv_tasks:
            tools_used.append("arxiv_search")
            arxiv_lists = await asyncio.gather(*arxiv_tasks, return_exceptions=True)
            for block in arxiv_lists:
                if isinstance(block, Exception):
                    logger.warning("arxiv task failed: %s", block)
                    continue
                for item in block:
                    new_evidence.append({"kind": "arxiv", **item})

    return new_evidence, tools_used


async def act_node(state: ResearchState) -> dict[str, Any]:
    tools_used = list(state.get("tools_used") or [])
    evidence = list(state.get("evidence") or [])
    act_count = int(state.get("act_count") or 0) + 1

    if settings.openai_api_key:
        new_evidence, agent_tools = await run_tool_agent(state)
        tools_used.extend([f"agent_tool:{x}" for x in agent_tools])
        merged = dedupe_evidence(evidence + new_evidence)
        logger.info(
            "act: mode=tool_agent pass=%s evidence=%s tools=%s",
            act_count,
            len(merged),
            agent_tools,
        )
    else:
        new_evidence, h_tools = await _heuristic_retrieval(state, act_count)
        tools_used.extend(h_tools)
        merged = dedupe_evidence(evidence + new_evidence)
        logger.info("act: mode=heuristic pass=%s evidence=%s", act_count, len(merged))

    return {
        "evidence": merged,
        "tools_used": tools_used,
        "act_count": act_count,
        "pending_tavily_queries": [],
        "pending_arxiv_queries": [],
    }
