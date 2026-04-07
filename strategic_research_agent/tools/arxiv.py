"""arXiv API search (Atom) — abstracts only, no PDF fetch (fast, reliable)."""

from __future__ import annotations

import logging
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.utils.http import get_async_client

logger = logging.getLogger(__name__)

_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


async def arxiv_search(query: str, max_results: int | None = None) -> list[dict[str, Any]]:
    max_results = max_results or settings.max_arxiv_results
    q = urllib.parse.quote(query)
    url = f"https://export.arxiv.org/api/query?search_query=all:{q}&start=0&max_results={max_results}"
    out: list[dict[str, Any]] = []
    try:
        async with get_async_client() as client:
            r = await client.get(url)
            r.raise_for_status()
            body = r.content
        root = ET.fromstring(body)
        for entry in root.findall("atom:entry", _NS):
            title = (entry.findtext("atom:title", default="", namespaces=_NS) or "").strip()
            published = (entry.findtext("atom:published", default="", namespaces=_NS) or "")[:10]
            abs_url = (entry.findtext("atom:id", default="", namespaces=_NS) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=_NS) or "").strip()
            authors: list[str] = []
            for a in entry.findall("atom:author", _NS):
                nm = a.findtext("atom:name", default="", namespaces=_NS)
                if nm:
                    authors.append(nm.strip())
            pdf_url = None
            for link in entry.findall("atom:link", _NS):
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href")
                    break
            out.append(
                {
                    "title": title,
                    "published": published,
                    "url": abs_url,
                    "pdfUrl": pdf_url,
                    "summary": summary[:4000],
                    "authors": authors,
                    "source": "arxiv",
                }
            )
        return out
    except Exception as e:
        logger.warning("arxiv search failed: %s", e)
        return [{"error": str(e), "source": "arxiv"}]
