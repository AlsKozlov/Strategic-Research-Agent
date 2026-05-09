"""Langfuse integration for Document Intelligence Agent.

Mirrors strategic_research_agent.observability.langfuse_client. Kept as a
separate module so each agent can be deployed independently with its own
settings namespace.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Callable

from document_intelligence_agent.config import settings

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    return bool(
        settings.langfuse_enabled
        and settings.langfuse_public_key
        and settings.langfuse_secret_key
    )


@lru_cache(maxsize=1)
def get_langfuse() -> Any | None:
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
            trace_name=trace_name or "document_intelligence",
            user_id=user_id,
            session_id=session_id,
            metadata={"service": settings.service_name, **(metadata or {})},
            tags=tags or [],
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("failed to build Langfuse callback handler: %s", e)
        return None


def observe(*dargs: Any, **dkwargs: Any) -> Callable[..., Any]:
    try:
        from langfuse.decorators import observe as _observe  # type: ignore
    except ImportError:
        if dargs and callable(dargs[0]) and not dkwargs:
            return dargs[0]

        def _noop(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return _noop

    if not _is_configured():
        if dargs and callable(dargs[0]) and not dkwargs:
            return dargs[0]

        def _passthrough(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return _passthrough

    return _observe(*dargs, **dkwargs)


def flush() -> None:
    client = get_langfuse()
    if client is not None:
        try:
            client.flush()
        except Exception:  # noqa: BLE001
            logger.debug("langfuse flush failed", exc_info=True)
