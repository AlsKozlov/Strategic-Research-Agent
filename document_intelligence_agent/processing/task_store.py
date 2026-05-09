from __future__ import annotations

import asyncio
import uuid
from typing import Any


class TaskStore:
    """In-memory A2A task store (JSON-serializable dicts)."""

    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}
        self._cancel: set[str] = set()
        self._lock = asyncio.Lock()

    async def save(self, task: dict[str, Any]) -> None:
        async with self._lock:
            self._tasks[task["id"]] = task

    async def get(self, task_id: str) -> dict[str, Any] | None:
        async with self._lock:
            t = self._tasks.get(task_id)
            return dict(t) if t else None

    async def list(
        self,
        context_id: str | None = None,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], str]:
        async with self._lock:
            items = list(self._tasks.values())
        if context_id:
            items = [t for t in items if t.get("contextId") == context_id]
        items.sort(key=lambda t: str(t.get("id")), reverse=True)
        return items[:page_size], ""

    def request_cancel(self, task_id: str) -> None:
        self._cancel.add(task_id)

    def is_cancelled(self, task_id: str) -> bool:
        return task_id in self._cancel


def new_task_id() -> str:
    return str(uuid.uuid4())


def result_to_artifact_dict(
    task_type: str,
    task_result: dict[str, Any],
    confidence: str,
    evidence: list[dict[str, Any]],
    gaps: list[str],
    latency_sec: float,
) -> dict[str, Any]:
    return {
        "taskType": task_type,
        "result": task_result,
        "confidence": confidence,
        "evidence": evidence,
        "gaps": gaps,
        "latencySec": round(latency_sec, 3),
    }
