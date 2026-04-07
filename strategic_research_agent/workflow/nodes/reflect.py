"""Reflect node: decide if another retrieval pass is needed."""

from __future__ import annotations

import json
import logging
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.utils.openai_client import AsyncOpenAI
from strategic_research_agent.workflow.nodes.common import clean_json_block, max_act_passes
from strategic_research_agent.workflow.nodes.evidence import evidence_digest
from strategic_research_agent.workflow.state import ResearchState

logger = logging.getLogger(__name__)

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def reflect_node(state: ResearchState) -> dict[str, Any]:
    act_count = int(state.get("act_count") or 0)
    if act_count >= max_act_passes():
        return {"needs_more": False, "reflection_notes": "max retrieval rounds reached"}

    if not settings.openai_api_key:
        return {"needs_more": False, "reflection_notes": "no LLM reflection (no OPENAI_API_KEY)"}

    digest = evidence_digest(state.get("evidence") or [])
    if not digest.strip():
        q = (state.get("query") or "").strip()
        return {
            "needs_more": True,
            "reflection_notes": "no evidence; retry with broader queries",
            "pending_tavily_queries": [q, f"{q} overview context"][:2],
            "pending_arxiv_queries": [q] if state.get("use_arxiv") else [],
        }

    client = _get_openai_client()
    system = (
        "You are the reflect step in PAR. Given the user query and evidence digest, "
        "decide if another retrieval pass is needed. Return ONLY JSON: "
        '{"needs_more": boolean, "notes": string, optional "pending_tavily_queries": string[], optional "pending_arxiv_queries": string[]}. '
        "If needs_more, propose 1-3 focused follow-up queries (not duplicates)."
    )
    user = json.dumps({"query": state.get("query"), "digest": digest}, ensure_ascii=False)
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = (resp.choices[0].message.content or "").strip()
    try:
        obj = json.loads(clean_json_block(raw))
    except json.JSONDecodeError:
        return {"needs_more": False, "reflection_notes": "reflect JSON parse failed"}

    needs = bool(obj.get("needs_more"))
    notes = str(obj.get("notes") or "")
    pt = [str(x) for x in (obj.get("pending_tavily_queries") or []) if str(x).strip()][:3]
    pa = [str(x) for x in (obj.get("pending_arxiv_queries") or []) if str(x).strip()][:2]

    if needs and not pt and not pa:
        needs = False

    logger.info("reflect: needs_more=%s act_count=%s", needs, act_count)
    return {
        "needs_more": needs,
        "reflection_notes": notes,
        "pending_tavily_queries": pt,
        "pending_arxiv_queries": pa,
        "tools_used": (state.get("tools_used") or []) + ["reflect"],
    }
