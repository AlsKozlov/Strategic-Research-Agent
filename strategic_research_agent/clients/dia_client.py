"""Async A2A client used by SRA to delegate document tasks to DIA.

The two agents are deliberately independent processes — they share no
database, no module imports, and no in-memory state. The only allowed
integration channel is HTTP A2A. This module is a thin, well-typed wrapper
around DIA's ``/message:send`` endpoint that:

* respects the global circuit breaker (``dia`` breaker name);
* applies a hard timeout (``settings.dia_a2a_timeout_sec``);
* returns a structured ``DIAResult`` instead of raw JSON;
* raises ``DIAUnavailable`` when the bridge is unconfigured so callers can
  fall back to in-process behavior without try/except gymnastics.

The bridge is **opt-in**: when ``settings.dia_a2a_base_url`` is ``None`` the
client refuses to start and any caller must check ``is_available`` first.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from strategic_research_agent.config import settings
from strategic_research_agent.utils.circuit_breaker import (
    CircuitOpenError,
    get_breaker,
)

logger = logging.getLogger(__name__)


class DIAClientError(RuntimeError):
    """DIA returned an error or unparsable payload."""


class DIAUnavailable(DIAClientError):
    """DIA bridge is not configured (``DIA_A2A_BASE_URL`` unset)."""


@dataclass
class DIAResult:
    task_type: str
    task_result: dict[str, Any]
    confidence: str
    evidence: list[dict[str, Any]]
    gaps: list[str]
    raw_artifact: dict[str, Any]


class DIAClient:
    """One client per process. Reuses a single ``httpx.AsyncClient`` so we
    benefit from connection pooling on repeated calls."""

    def __init__(self, base_url: str, timeout_sec: float) -> None:
        self._base_url = base_url.rstrip("/")
        # Eager construction avoids a TOCTOU race in which two concurrent
        # callers would each spawn their own AsyncClient and leak the loser.
        # httpx.AsyncClient is cheap to instantiate and lazy on the actual
        # connection pool, so eager creation is safe.
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout_sec,
            headers={"User-Agent": f"{settings.service_name}/dia-bridge"},
        )
        self._breaker = get_breaker("dia")

    async def __aenter__(self) -> DIAClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if not self._client.is_closed:
            await self._client.aclose()

    def check_available(self) -> bool:
        """Returns True if the breaker is currently closed.

        Note: this method has a side effect — it transitions the breaker from
        open → half-open if the cooldown has elapsed. Call it from the
        scheduling decision point, not as a pure predicate.
        """
        return not self._breaker.is_open

    # ── Public API ────────────────────────────────────────────────────────────

    async def analyze_document(
        self,
        instruction: str,
        document: str,
        *,
        task_hint: str | None = None,
    ) -> DIAResult:
        """Send a single document to DIA and return the parsed artifact.

        ``task_hint`` is forwarded as ``metadata.summaryFormat`` and is purely
        advisory — DIA's classify node makes the final decision.
        """
        client = await self._ensure_client()

        message: dict[str, Any] = {
            "messageId": str(uuid.uuid4()),
            "role": "ROLE_USER",
            "parts": [
                {"text": instruction, "mediaType": "text/plain"},
                {"text": document, "mediaType": "text/plain"},
            ],
            "metadata": {"instruction": instruction},
        }
        if task_hint:
            message["metadata"]["summaryFormat"] = task_hint

        body = {
            "message": message,
            "configuration": {"returnImmediately": False},
        }

        async def _post() -> httpx.Response:
            return await client.post("/message:send", json=body)

        try:
            resp = await self._breaker.run_async(_post)
        except CircuitOpenError as e:
            raise DIAUnavailable("DIA breaker is open") from e
        except httpx.HTTPError as e:
            raise DIAClientError(f"DIA HTTP error: {e}") from e

        if resp.status_code >= 400:
            raise DIAClientError(f"DIA returned {resp.status_code}: {resp.text[:200]}")

        try:
            payload = resp.json()
        except ValueError as e:
            raise DIAClientError("DIA returned non-JSON body") from e

        return self._parse(payload)

    # ── Parsing ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse(payload: dict[str, Any]) -> DIAResult:
        task = payload.get("task") or payload
        artifacts = task.get("artifacts") or []
        if not artifacts:
            raise DIAClientError("DIA response had no artifacts")
        artifact = artifacts[0]
        data: dict[str, Any] = {}
        for part in artifact.get("parts") or []:
            if isinstance(part, dict) and isinstance(part.get("data"), dict):
                data = part["data"]
                break
        if not data:
            raise DIAClientError("DIA artifact had no JSON data part")

        return DIAResult(
            task_type=str(data.get("task_type") or "unknown"),
            task_result=dict(data.get("task_result") or {}),
            confidence=str(data.get("confidence") or "low"),
            evidence=list(data.get("evidence") or []),
            gaps=list(data.get("gaps") or []),
            raw_artifact=artifact,
        )


# ── Singleton accessor ────────────────────────────────────────────────────────

_singleton: DIAClient | None = None


def get_dia_client() -> DIAClient:
    """Return the process-wide DIA client.

    Raises :class:`DIAUnavailable` if the bridge is not configured. Callers
    should treat that as "fall back to local behaviour" — the bridge is
    deliberately optional.
    """
    global _singleton
    if not settings.dia_a2a_base_url:
        raise DIAUnavailable("DIA_A2A_BASE_URL is not set")
    if _singleton is None:
        _singleton = DIAClient(
            base_url=settings.dia_a2a_base_url,
            timeout_sec=settings.dia_a2a_timeout_sec,
        )
    return _singleton


__all__ = ["DIAClient", "DIAClientError", "DIAResult", "DIAUnavailable", "get_dia_client"]
