from __future__ import annotations

import asyncio
import uuid
from typing import Any

from strategic_research_agent.research.engine import ResearchResult


class TaskStore:
    """In-memory A2A task documents (JSON-serializable dicts)."""

    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}
        self._cancel: set[str] = set()
        self._lock = asyncio.Lock()

    async def save(self, task: dict[str, Any]) -> None:
        tid = task["id"]
        async with self._lock:
            self._tasks[tid] = task

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
        page = items[:page_size]
        return page, ""

    def request_cancel(self, task_id: str) -> None:
        self._cancel.add(task_id)

    def is_cancelled(self, task_id: str) -> bool:
        return task_id in self._cancel


def research_to_artifact_dict(result: ResearchResult) -> dict[str, Any]:
    return {
        "query": result.query,
        "researchPlan": result.research_plan,
        "confidence": result.confidence,
        "caveats": result.caveats,
        "latencySec": round(result.latency_sec, 3),
        "webSources": [
            {"title": h.title, "url": h.url, "snippet": h.snippet} for h in result.web_hits
        ],
        "arxivHits": result.arxiv_hits,
        "markdownReport": result.report_markdown,
        "metadata": result.metadata,
    }


def new_task_id() -> str:
    return str(uuid.uuid4())
