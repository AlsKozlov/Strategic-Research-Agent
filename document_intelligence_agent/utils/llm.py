"""Shared async OpenAI client — created once per process, reused across requests."""

from __future__ import annotations

from document_intelligence_agent.config import settings

_client = None


def get_llm_client():
    """Return the module-level AsyncOpenAI singleton (initialised on first call)."""
    global _client
    if _client is None:
        try:
            from langfuse.openai import AsyncOpenAI  # type: ignore
        except ImportError:
            from openai import AsyncOpenAI  # type: ignore

        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client
