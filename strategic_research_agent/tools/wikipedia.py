"""Wikipedia search via REST API — background facts and topic overviews."""

from __future__ import annotations

import asyncio
import logging
import urllib.parse
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.utils.http import get_async_client

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"


async def wikipedia_search(query: str, max_results: int | None = None) -> list[dict[str, Any]]:
    """Search Wikipedia and return article summaries with full extracts."""
    n = max_results or getattr(settings, "max_wikipedia_results", 3)
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": str(n),
        "format": "json",
        "utf8": "1",
        "srprop": "snippet",
    }
    out: list[dict[str, Any]] = []
    try:
        async with get_async_client(timeout=25.0) as client:
            r = await client.get(_SEARCH_URL, params=params)
            r.raise_for_status()
            data = r.json()
            results = (data.get("query") or {}).get("search") or []
            titles = [res["title"] for res in results[:n] if res.get("title")]
            if not titles:
                return []

            async def fetch_summary(title: str) -> dict[str, Any] | None:
                encoded = urllib.parse.quote(title.replace(" ", "_"))
                url = _SUMMARY_URL.format(encoded)
                try:
                    sr = await client.get(url)
                    sr.raise_for_status()
                    s = sr.json()
                    page_url = (
                        (s.get("content_urls") or {})
                        .get("desktop", {})
                        .get("page")
                        or f"https://en.wikipedia.org/wiki/{encoded}"
                    )
                    extract = (s.get("extract") or "").strip()
                    description = (s.get("description") or "").strip()
                    return {
                        "title": s.get("title") or title,
                        "url": page_url,
                        "summary": extract[:4000],
                        "description": description,
                        "source": "wikipedia",
                    }
                except Exception as e:
                    logger.debug("wikipedia summary fetch failed for %s: %s", title, e)
                    return None

            summaries = await asyncio.gather(*[fetch_summary(t) for t in titles])
            for s in summaries:
                if s:
                    out.append(s)
    except Exception as e:
        logger.warning("wikipedia search failed: %s", e)
        return [{"error": str(e), "source": "wikipedia"}]
    return out
