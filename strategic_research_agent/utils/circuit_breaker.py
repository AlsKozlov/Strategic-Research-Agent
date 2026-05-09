"""In-process circuit breaker for external dependencies.

A breaker keeps a per-dependency failure count. After ``fail_threshold``
consecutive failures it opens the circuit and short-circuits subsequent
calls with :class:`CircuitOpenError` until ``cooldown_sec`` elapses, after
which the breaker enters a half-open state and allows one probe call.

This is intentionally a tiny, dependency-free implementation. We do not need
distributed state — each agent process keeps its own breaker, which is the
right granularity for the PoC because each container has a single replica.

Usage:

    breaker = get_breaker("tavily")
    try:
        result = breaker.run_sync(lambda: tavily_call())
    except CircuitOpenError:
        ...  # fall back

The breaker is safe under asyncio because all state mutations happen in the
calling task without yielding the event loop.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from strategic_research_agent.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised by a breaker that is currently open."""


_STATE_CLOSED = "closed"
_STATE_OPEN = "open"
_STATE_HALF = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    fail_threshold: int
    cooldown_sec: float

    _state: str = _STATE_CLOSED
    _failures: int = 0
    _opened_at: float = 0.0

    # ── State helpers ─────────────────────────────────────────────────────────

    def _maybe_close_after_cooldown(self) -> None:
        if self._state == _STATE_OPEN and (time.monotonic() - self._opened_at) >= self.cooldown_sec:
            logger.info("breaker %s entering half-open after cooldown", self.name)
            self._state = _STATE_HALF

    def _record_success(self) -> None:
        if self._state != _STATE_CLOSED:
            logger.info("breaker %s closing after successful probe", self.name)
        self._state = _STATE_CLOSED
        self._failures = 0

    def _record_failure(self, exc: BaseException) -> None:
        self._failures += 1
        if self._state == _STATE_HALF or self._failures >= self.fail_threshold:
            self._state = _STATE_OPEN
            self._opened_at = time.monotonic()
            logger.warning(
                "breaker %s OPEN after %d failures (last=%s)",
                self.name,
                self._failures,
                exc.__class__.__name__,
            )

    def _guard(self) -> None:
        self._maybe_close_after_cooldown()
        if self._state == _STATE_OPEN:
            raise CircuitOpenError(f"circuit '{self.name}' is open")

    # ── Sync / async wrappers ─────────────────────────────────────────────────

    def run_sync(self, fn: Callable[[], T]) -> T:
        self._guard()
        try:
            out = fn()
        except BaseException as e:
            self._record_failure(e)
            raise
        self._record_success()
        return out

    async def run_async(self, fn: Callable[[], Awaitable[T]]) -> T:
        self._guard()
        try:
            out = await fn()
        except BaseException as e:
            self._record_failure(e)
            raise
        self._record_success()
        return out

    @property
    def is_open(self) -> bool:
        self._maybe_close_after_cooldown()
        return self._state == _STATE_OPEN


# ── Registry ──────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, CircuitBreaker] = {}


def get_breaker(
    name: str,
    *,
    fail_threshold: int | None = None,
    cooldown_sec: float | None = None,
) -> CircuitBreaker:
    """Return (and lazily create) the named breaker.

    Defaults pull from ``settings.breaker_fail_threshold`` /
    ``settings.breaker_cooldown_sec`` so they can be tuned per-deployment
    without code changes.

    Concurrency: ``dict.setdefault`` is atomic under CPython's GIL, so two
    concurrent callers will always end up sharing the same breaker instance.
    """
    cb = CircuitBreaker(
        name=name,
        fail_threshold=fail_threshold or settings.breaker_fail_threshold,
        cooldown_sec=cooldown_sec or settings.breaker_cooldown_sec,
    )
    return _REGISTRY.setdefault(name, cb)


def reset_all() -> None:
    """Test helper — drop registered breakers."""
    _REGISTRY.clear()


__all__ = ["CircuitBreaker", "CircuitOpenError", "get_breaker", "reset_all"]
