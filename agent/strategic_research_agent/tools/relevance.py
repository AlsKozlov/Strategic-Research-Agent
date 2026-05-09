"""Score whether page text helps answer the research question (LLM or heuristic)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from strategic_research_agent.config import settings

logger = logging.getLogger(__name__)

_SCORE_SCHEMA = (
    '{"helpful": <bool>, "score": <0.0-1.0>, "reason": "<short>"}'
)


def _heuristic_score(user_query: str, title: str, text: str) -> dict[str, Any]:
    q = re.findall(r"[\w']+", (user_query or "").lower())
    blob = f"{title} {text}".lower()
    words = set(re.findall(r"[\w']+", blob))
    qset = set(q)
    if not qset:
        return {"helpful": False, "score": 0.0, "reason": "empty query"}
    inter = len(qset & words)
    union = len(qset | words) or 1
    jaccard = inter / max(len(qset), 1)
    score = min(1.0, 0.35 + 0.65 * jaccard)
    helpful = score >= float(settings.deep_web_min_relevance)
    return {"helpful": helpful, "score": round(score, 3), "reason": "keyword_overlap"}


async def score_content_relevance(
    user_query: str,
    title: str,
    text: str,
    max_chars: int = 8000,
) -> dict[str, Any]:
    """Return ``{helpful, score, reason}``."""
    snippet = (text or "")[:max_chars]
    if not settings.openai_api_key:
        return _heuristic_score(user_query, title, snippet)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    user_msg = (
        f"Research question:\n{user_query}\n\n"
        f"Page title: {title}\n\n"
        f"Page text (excerpt):\n{snippet}\n\n"
        f"Reply with JSON only: {_SCORE_SCHEMA}"
    )
    try:
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You judge if the page content can help answer the research question. "
                        "Be strict: marketing fluff or tangential pages get low scores. "
                        "Output valid JSON only."
                    ),
                },
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=256,
        )
        raw = (resp.choices[0].message.content or "").strip()
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            raw = m.group(0)
        data = json.loads(raw)
        score = float(data.get("score", 0.0))
        score = max(0.0, min(1.0, score))
        helpful = bool(data.get("helpful", score >= settings.deep_web_min_relevance))
        return {
            "helpful": helpful,
            "score": round(score, 3),
            "reason": str(data.get("reason") or "")[:240],
        }
    except Exception as e:
        logger.warning("relevance LLM failed, heuristic: %s", e)
        return _heuristic_score(user_query, title, snippet)


async def refine_search_query(user_query: str, failed_query: str, iteration: int) -> str:
    """One alternative search string for the next Tavily iteration."""
    if not settings.openai_api_key:
        extra = " review OR benchmark OR documentation"
        return (failed_query + extra)[:280]

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = (
        f"Original information need:\n{user_query}\n\n"
        f"Previous search query that yielded weak pages:\n{failed_query}\n\n"
        f"Iteration: {iteration}. Propose ONE improved web search query (English), "
        "more specific or using alternate keywords. Reply with the query line only, no quotes."
    )
    try:
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
            max_tokens=120,
        )
        line = (resp.choices[0].message.content or "").strip().split("\n")[0].strip()
        line = line.strip("\"'")
        return line[:400] if line else failed_query
    except Exception as e:
        logger.warning("refine_search_query failed: %s", e)
        return (failed_query + " alternative terms")[:400]
