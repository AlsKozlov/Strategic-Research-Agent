"""Langfuse integration for Strategic Research Agent.

Provides:
- A process-wide singleton Langfuse client (lazy, only when enabled).
- A factory for the LangChain CallbackHandler used by LangGraph nodes.
- A no-op `observe` decorator passthrough so call sites stay clean even when
  Langfuse is disabled or not installed.

Usage:
    from strategic_research_agent.observability.langfuse_client import (
        get_langfuse, get_langchain_handler, observe,
    )

    @observe(name="run_research")
    async def run_research(...): ...

    handler = get_langchain_handler(trace_name="research_graph", metadata={...})
    await graph.ainvoke(state, config={"callbacks": [handler] if handler else []})
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Callable

from strategic_research_agent.config import settings

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    return bool(
        settings.langfuse_enabled
        and settings.langfuse_public_key
        and settings.langfuse_secret_key
    )


@lru_cache(maxsize=1)
def get_langfuse() -> Any | None:
    """Return a singleton Langfuse client, or None when disabled/misconfigured."""
    if not _is_configured():
        return None
    try:
        from langfuse import Langfuse  # type: ignore
    except ImportError:
        logger.warning("langfuse not installed; observability disabled")
        return None
    try:
        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            release=settings.langfuse_release,
            sample_rate=settings.langfuse_sample_rate,
        )
        logger.info(
            "Langfuse initialized: host=%s sample_rate=%.2f",
            settings.langfuse_host,
            settings.langfuse_sample_rate,
        )
        return client
    except Exception as e:  # noqa: BLE001
        logger.exception("failed to initialize Langfuse: %s", e)
        return None


def get_langchain_handler(
    *,
    trace_name: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Any | None:
    """Return a LangChain CallbackHandler bound to the singleton Langfuse client.

    Returns None when Langfuse is disabled — callers should pass `[handler]`
    only when not None.
    """
    client = get_langfuse()
    if client is None:
        return None
    try:
        from langfuse.callback import CallbackHandler  # type: ignore
    except ImportError:
        return None
    try:
        return CallbackHandler(
            stateful_client=client,
            trace_name=trace_name or "research_graph",
            user_id=user_id,
            session_id=session_id,
            metadata={"service": settings.service_name, **(metadata or {})},
            tags=tags or [],
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("failed to build Langfuse callback handler: %s", e)
        return None


def observe(*dargs: Any, **dkwargs: Any) -> Callable[..., Any]:
    """Drop-in `@observe` that becomes a no-op when Langfuse is unavailable.

    Mirrors `langfuse.decorators.observe` API. When the SDK is missing or
    disabled, returns the original function untouched so we never crash on
    import in dev environments.
    """
    try:
        from langfuse.decorators import observe as _observe  # type: ignore
    except ImportError:
        def _noop_decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        # Support both @observe and @observe(name=...)
        if dargs and callable(dargs[0]) and not dkwargs:
            return dargs[0]
        return _noop_decorator

    if not _is_configured():
        if dargs and callable(dargs[0]) and not dkwargs:
            return dargs[0]

        def _passthrough(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return _passthrough

    return _observe(*dargs, **dkwargs)


def flush() -> None:
    """Flush pending Langfuse events. Call on shutdown."""
    client = get_langfuse()
    if client is not None:
        try:
            client.flush()
        except Exception:  # noqa: BLE001
            logger.debug("langfuse flush failed", exc_info=True)
