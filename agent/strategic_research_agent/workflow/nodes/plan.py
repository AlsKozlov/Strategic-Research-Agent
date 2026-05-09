"""Plan node: classify task, choose tools, seed queries."""

from __future__ import annotations

import json
import logging
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.tools.aggregators import infer_task_type, select_aggregators
from strategic_research_agent.workflow.nodes.common import clean_json_block
from strategic_research_agent.workflow.state import ResearchState

logger = logging.getLogger(__name__)


def heuristic_plan(query: str) -> dict[str, Any]:
    tt = infer_task_type(query)
    domains = select_aggregators(tt, query)
    return {
        "task_type": tt,
        "plan_steps": [
            "Plan: classify task and select tools (Tavily, arXiv, aggregator-scoped Tavily)",
            "Act: retrieve sources with selected tools",
            "Reflect: check coverage gaps (optional)",
            "Synthesize: structured report with citations and confidence",
        ],
        "use_tavily": True,
        "use_arxiv": tt in ("academic", "compare", "general", "market"),
        "use_aggregator_scoped_tavily": True,
        "tavily_queries": [query],
        "arxiv_queries": [query],
        "aggregator_domains": domains,
    }


def normalize_plan(raw: Any, query: str) -> dict[str, Any]:
    q = (query or "").strip()
    if not isinstance(raw, dict):
        return heuristic_plan(q)
    tt = str(raw.get("task_type") or infer_task_type(q))
    steps = raw.get("plan_steps")
    if not isinstance(steps, list):
        steps = []
    steps = [str(s).strip() for s in steps if str(s).strip()][:6]
    tq = [str(x).strip() for x in (raw.get("tavily_queries") or []) if str(x).strip()][:4]
    aq = [str(x).strip() for x in (raw.get("arxiv_queries") or []) if str(x).strip()][:3]
    return {
        "task_type": tt,
        "plan_steps": steps,
        "use_tavily": bool(raw.get("use_tavily", True)),
        "use_arxiv": bool(raw.get("use_arxiv", True)),
        "use_aggregator_scoped_tavily": bool(raw.get("use_aggregator_scoped_tavily", True)),
        "tavily_queries": tq,
        "arxiv_queries": aq,
        "aggregator_domains": [str(x).strip() for x in (raw.get("aggregator_domains") or []) if str(x).strip()][
            :4
        ],
    }


async def llm_plan(query: str) -> dict[str, Any]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    system = (
        "You are the planning module of Strategic Research Agent (PAR). "
        "Return ONLY valid JSON with keys: "
        "task_type (market|company|compare|academic|general), "
        "plan_steps (string array, max 6) — high-level investigation angles only, NOT concrete search queries, "
        "aggregator_domains (string array, 0-4 hostname hints for optional scoped search), "
        "optional: use_tavily (bool, default true), use_arxiv (bool, default true), "
        "use_aggregator_scoped_tavily (bool, default true). "
        "Do NOT output tavily_queries or arxiv_queries — a separate retrieval agent will choose tools (web, arXiv, scoped) and queries."
    )
    user = f"User research request:\n{query}"
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        return normalize_plan(json.loads(clean_json_block(raw)), query)
    except json.JSONDecodeError:
        logger.warning("plan JSON parse failed; using heuristic plan")
        return normalize_plan(heuristic_plan(query), query)


async def plan_node(state: ResearchState) -> dict[str, Any]:
    q = state.get("query") or ""
    if not settings.openai_api_key:
        p = normalize_plan(heuristic_plan(q), q)
    else:
        p = await llm_plan(q)

    tt = str(p.get("task_type") or infer_task_type(q))
    if not p.get("aggregator_domains"):
        p["aggregator_domains"] = select_aggregators(tt, q)

    use_arxiv = bool(p.get("use_arxiv", True))
    arxiv_queries = list(p.get("arxiv_queries") or []) if use_arxiv else []
    if not settings.openai_api_key:
        if not p.get("tavily_queries"):
            p["tavily_queries"] = [q]
        if use_arxiv and not arxiv_queries:
            arxiv_queries = [q]

    logger.info(
        "plan: task_type=%s tavily=%s arxiv=%s agg=%s",
        tt,
        p.get("use_tavily"),
        use_arxiv,
        p.get("use_aggregator_scoped_tavily"),
    )

    return {
        "task_type": tt,
        "plan_steps": list(p.get("plan_steps") or [])[:6],
        "use_tavily": bool(p.get("use_tavily", True)),
        "use_arxiv": use_arxiv,
        "use_aggregator_scoped_tavily": bool(p.get("use_aggregator_scoped_tavily", True)),
        "tavily_queries": list(p.get("tavily_queries") or [q])[:4],
        "arxiv_queries": arxiv_queries[:3],
        "aggregator_domains": list(p.get("aggregator_domains") or [])[:4],
        "tools_used": ["plan"],
        "act_count": 0,
        "needs_more": False,
        "evidence": [],
        "errors": [],
    }
