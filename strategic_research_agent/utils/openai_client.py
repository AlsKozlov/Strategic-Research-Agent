"""OpenAI client shim that auto-instruments via Langfuse when available.

Importing from `langfuse.openai` returns a drop-in replacement for the OpenAI
SDK that emits Langfuse traces (generations) for every call without any code
changes at the call site. When the Langfuse SDK is not installed we fall back
to the vanilla SDK so dev environments still work.

Usage:
    from strategic_research_agent.utils.openai_client import AsyncOpenAI
"""

from __future__ import annotations

try:
    from langfuse.openai import AsyncOpenAI  # type: ignore
except ImportError:  # pragma: no cover - fallback for envs without langfuse
    from openai import AsyncOpenAI  # type: ignore

__all__ = ["AsyncOpenAI"]
