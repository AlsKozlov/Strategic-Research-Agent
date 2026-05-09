"""Fetch HTML and extract main text (trafilatura)."""

from __future__ import annotations

import logging
from typing import Any

import trafilatura

from strategic_research_agent.config import settings
from strategic_research_agent.utils.http import get_sync_client
from strategic_research_agent.utils.retry import run_with_retries

logger = logging.getLogger(__name__)

_THIN_THRESHOLD = 320


def fetch_and_extract(url: str, timeout: float | None = None) -> dict[str, Any]:
    """GET ``url`` and return ``{ok, url, title, text, error}``."""
    timeout = timeout if timeout is not None else float(settings.deep_web_fetch_timeout_sec)

    def _once() -> dict[str, Any]:
        with get_sync_client(timeout=timeout) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text
        extracted = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
        )
        meta = trafilatura.extract_metadata(html) or None
        title = (meta.title if meta and meta.title else "") or ""
        text = (extracted or "").strip()
        if len(text) < 80:
            return {
                "ok": False,
                "url": url,
                "title": title,
                "text": text,
                "error": "thin_extract",
            }
        return {"ok": True, "url": url, "title": title, "text": text, "error": None}

    try:
        return run_with_retries(
            _once,
            attempts=settings.search_retry_attempts,
            base_delay_sec=settings.search_retry_delay_sec,
            label="fetch_and_extract",
        )
    except Exception as e:
        logger.debug("fetch failed %s: %s", url, e)
        return {"ok": False, "url": url, "title": "", "text": "", "error": str(e)}


def merge_snippet_and_raw(row: dict[str, Any]) -> str:
    """Prefer raw_content, else content."""
    raw = row.get("raw_content")
    if raw and len(str(raw).strip()) >= _THIN_THRESHOLD:
        return str(raw).strip()
    c = row.get("content") or ""
    return str(c).strip()


def needs_fetch(row: dict[str, Any]) -> bool:
    """True if on-page extraction is likely to add value."""
    merged = merge_snippet_and_raw(row)
    return len(merged) < _THIN_THRESHOLD
