"""Tavily web search; falls back to DuckDuckGo if `TAVILY_API_KEY` is unset."""

from __future__ import annotations

import logging
from typing import Any

from duckduckgo_search import DDGS

from strategic_research_agent.config import settings
from strategic_research_agent.utils.circuit_breaker import (
    CircuitOpenError,
    get_breaker,
)
from strategic_research_agent.utils.retry import run_with_retries

logger = logging.getLogger(__name__)


def tavily_search(
    query: str,
    max_results: int | None = None,
    include_domains: list[str] | None = None,
    *,
    search_depth: str | None = None,
    include_raw_content: bool = False,
) -> list[dict[str, Any]]:
    """Return list of {title, url, content} (Tavily) or {title, url, content} from DDG fallback.

    Optional ``search_depth`` (``basic`` | ``advanced``) and ``include_raw_content`` apply to Tavily only.
    """
    max_results = max_results or settings.max_web_results
    tavily_breaker = get_breaker("tavily")
    ddg_breaker = get_breaker("duckduckgo")

    if settings.tavily_api_key and not tavily_breaker.is_open:
        try:
            from tavily import TavilyClient

            def _tavily_once() -> list[dict[str, Any]]:
                client = TavilyClient(api_key=settings.tavily_api_key)
                kwargs: dict[str, Any] = {"query": query, "max_results": max_results}
                if include_domains:
                    kwargs["include_domains"] = include_domains
                if search_depth is not None:
                    kwargs["search_depth"] = search_depth
                elif include_raw_content:
                    kwargs["search_depth"] = getattr(settings, "tavily_search_depth", "advanced")
                if include_raw_content:
                    kwargs["include_raw_content"] = True
                resp = client.search(**kwargs)
                out: list[dict[str, Any]] = []
                for r in resp.get("results") or []:
                    row: dict[str, Any] = {
                        "title": r.get("title") or "",
                        "url": r.get("url") or "",
                        "content": r.get("content") or "",
                        "source": "tavily",
                    }
                    raw = r.get("raw_content")
                    if raw:
                        row["raw_content"] = str(raw)
                    score = r.get("score")
                    if score is not None:
                        row["tavily_score"] = score
                    out.append(row)
                return out

            return tavily_breaker.run_sync(
                lambda: run_with_retries(
                    _tavily_once,
                    attempts=settings.search_retry_attempts,
                    base_delay_sec=settings.search_retry_delay_sec,
                    label="tavily_search",
                )
            )
        except CircuitOpenError:
            logger.info("Tavily breaker open; using DDG fallback")
        except Exception as e:
            logger.warning("Tavily search failed, falling back: %s", e)

    # Fallback: DDG cannot honor include_domains precisely; add query hints.
    q = query
    if include_domains:
        site = include_domains[0]
        q = f"{query} site:{site}"
    def _ddg_once() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with DDGS() as ddgs:
            for r in ddgs.text(q, max_results=max_results):
                rows.append(
                    {
                        "title": str(r.get("title") or ""),
                        "url": str(r.get("href") or r.get("url") or ""),
                        "content": str(r.get("body") or ""),
                        "source": "duckduckgo",
                    }
                )
        return rows

    if ddg_breaker.is_open:
        logger.info("DDG breaker open; returning empty result")
        return []
    try:
        return ddg_breaker.run_sync(
            lambda: run_with_retries(
                _ddg_once,
                attempts=settings.search_retry_attempts,
                base_delay_sec=settings.search_retry_delay_sec,
                label="duckduckgo_search",
            )
        )
    except CircuitOpenError:
        return []
    except Exception as e:
        logger.warning("fallback web search failed: %s", e)
    return []
