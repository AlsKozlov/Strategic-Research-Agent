"""LLM-driven tool loop: model chooses web_search, arxiv_search, web_search_on_sites."""

from __future__ import annotations

import json
import logging
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.tools.aggregators import list_aggregator_catalog
from strategic_research_agent.tools.definitions import OPENAI_RESEARCH_TOOLS
from strategic_research_agent.tools.executor import execute_research_tool, summarize_tool_result_for_llm
from strategic_research_agent.workflow.state import ResearchState

logger = logging.getLogger(__name__)


def _catalog_digest() -> str:
    try:
        cat = list_aggregator_catalog()
        lines = [f"- {c['id']}: {', '.join(c.get('domains', [])[:2])}" for c in cat[:12]]
        return "\n".join(lines)
    except Exception:
        return "(catalog unavailable)"


def _build_user_message(state: ResearchState) -> str:
    q = (state.get("query") or "").strip()
    parts: list[str] = [f"## Research request\n{q}"]
    kb = state.get("kb_context") or []
    if kb:
        parts.append("## Internal KB context\n" + "\n\n".join(str(s)[:4000] for s in kb[:8]))
    tt = state.get("task_type")
    if tt:
        parts.append(f"## Task type (hint)\n{tt}")
    steps = state.get("plan_steps") or []
    if steps:
        parts.append("## Investigation angles (hints, not mandatory)\n" + "\n".join(f"- {s}" for s in steps))
    doms = state.get("aggregator_domains") or []
    if doms:
        parts.append(
            "## Suggested domains for `web_search_on_sites` if relevant\n"
            + ", ".join(doms)
        )
    pt = state.get("pending_tavily_queries") or []
    pa = state.get("pending_arxiv_queries") or []
    if pt or pa:
        parts.append("## Follow-up focus (this retrieval pass)\n")
        for x in pt:
            parts.append(f"- Prefer web search: {x}")
        for x in pa:
            parts.append(f"- Prefer arXiv: {x}")
    return "\n\n".join(parts)


def _system_prompt() -> str:
    return (
        "You are the retrieval agent for Strategic Research. "
        "You MUST call tools to fetch real sources — use `web_search` for quick broad web, "
        "`deep_web_research` when you need full-page extraction, relevance filtering, and automatic "
        "retries/refined queries (complex facts, comparisons, technical depth); "
        "`arxiv_search` for papers/preprints, `web_search_on_sites` when a specific site class matters "
        "(e.g. sec.gov filings, g2.com reviews). "
        "You may call tools multiple times with different queries. "
        "When you have enough diverse evidence, stop calling tools and reply with one short sentence "
        "summarizing what you gathered (no bullet lists).\n\n"
        "Aggregator catalog (for scoped search):\n"
        f"{_catalog_digest()}"
    )


async def run_tool_agent(state: ResearchState) -> tuple[list[dict[str, Any]], list[str]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": _build_user_message(state)},
    ]
    collected: list[dict[str, Any]] = []
    tools_log: list[str] = []
    max_it = max(1, int(settings.tool_agent_max_iterations))

    for i in range(max_it):
        kwargs: dict[str, Any] = {
            "model": settings.openai_model,
            "messages": messages,
            "tools": OPENAI_RESEARCH_TOOLS,
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        if i == 0:
            kwargs["tool_choice"] = "required"
        else:
            kwargs["tool_choice"] = "auto"

        resp = await client.chat.completions.create(**kwargs)
        choice = resp.choices[0].message
        if not choice.tool_calls:
            if choice.content:
                messages.append({"role": "assistant", "content": choice.content})
            break

        messages.append(
            {
                "role": "assistant",
                "content": choice.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in choice.tool_calls
                ],
            }
        )

        for tc in choice.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tools_log.append(name)
            rows = await execute_research_tool(name, args)
            for row in rows:
                if row.get("kind") == "error":
                    logger.warning("tool_agent error: %s", row)
                    continue
                collected.append(row)
            payload = summarize_tool_result_for_llm([r for r in rows if r.get("kind") != "error"])
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": payload or "[]",
                }
            )
            logger.info("tool_agent: %s -> %s rows", name, len(rows))

    return collected, tools_log
