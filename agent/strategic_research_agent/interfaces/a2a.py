from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from strategic_research_agent.config import settings
from strategic_research_agent.discovery.agent_card import build_agent_card
from strategic_research_agent.observability.logging import configure_logging
from strategic_research_agent.research.engine import run_research
from strategic_research_agent.research.task_store import TaskStore, new_task_id, research_to_artifact_dict

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Strategic Research Agent (A2A)")
store = TaskStore()
_bg_tasks: set[asyncio.Task] = set()


def _get(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _parts_to_text(parts: list[Any]) -> str:
    chunks: list[str] = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        t = _get(p, "text")
        if isinstance(t, str) and t.strip():
            chunks.append(t)
    return "\n".join(chunks).strip()


def _kb_from_metadata(metadata: dict[str, Any] | None) -> list[str]:
    if not metadata:
        return []
    raw = _get(metadata, "kbContext", "kb_context")
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return []


def _task_status(state: str, text: str | None = None) -> dict[str, Any]:
    msg: dict[str, Any] | None = None
    if text is not None:
        msg = {
            "messageId": str(uuid.uuid4()),
            "role": "ROLE_AGENT",
            "parts": [{"text": text, "mediaType": "text/plain"}],
        }
    return {"state": state, "message": msg}


async def _run_and_finalize(
    task_id: str,
    context_id: str,
    user_text: str,
    kb: list[str],
) -> None:
    try:
        if store.is_cancelled(task_id):
            t = await store.get(task_id)
            if t:
                t["status"] = _task_status("TASK_STATE_CANCELED", "Canceled.")
                await store.save(t)
            return
        result = await run_research(user_text, kb)
        data = research_to_artifact_dict(result)
        artifact = {
            "artifactId": str(uuid.uuid4()),
            "name": "research_report",
            "description": "Structured research output (JSON + markdown)",
            "parts": [
                {"mediaType": "application/json", "data": data},
                {"text": result.report_markdown, "mediaType": "text/markdown"},
            ],
        }
        summary = (
            f"Research completed. Confidence: {result.confidence}. "
            f"See artifact `research_report` for full report and sources."
        )
        t = await store.get(task_id)
        if not t:
            return
        t["status"] = _task_status("TASK_STATE_COMPLETED", summary)
        t["artifacts"] = [artifact]
        hist = list(t.get("history") or [])
        hist.append(
            {
                "messageId": str(uuid.uuid4()),
                "contextId": context_id,
                "taskId": task_id,
                "role": "ROLE_AGENT",
                "parts": [{"text": summary, "mediaType": "text/plain"}],
            }
        )
        t["history"] = hist
        await store.save(t)
        logger.info(
            "task %s completed in %.3fs", task_id, result.latency_sec,
        )
    except Exception as e:
        logger.exception("task %s failed: %s", task_id, e)
        t = await store.get(task_id)
        if t:
            t["status"] = _task_status("TASK_STATE_FAILED", str(e))
            await store.save(t)


def _schedule_bg(coro: Any) -> None:
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


@app.get("/.well-known/agent.json")
async def well_known_agent() -> dict[str, Any]:
    return build_agent_card()


@app.get("/extendedAgentCard")
@app.get("/{tenant}/extendedAgentCard")
async def extended_agent_card(tenant: str | None = None) -> dict[str, Any]:
    _ = tenant
    return build_agent_card()


async def _handle_send_message(body: dict[str, Any], tenant: str | None) -> dict[str, Any]:
    _ = tenant
    msg = body.get("message") or {}
    parts = msg.get("parts") or []
    if not isinstance(parts, list):
        raise HTTPException(400, "message.parts must be a list")
    user_text = _parts_to_text(parts)
    if not user_text:
        raise HTTPException(400, "empty message (no text parts)")

    cfg = body.get("configuration") or {}
    return_immediately = bool(
        _get(cfg, "returnImmediately", "return_immediately") or False,
    )
    metadata = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else body.get("metadata")
    kb = _kb_from_metadata(metadata if isinstance(metadata, dict) else None)

    context_id = str(_get(msg, "contextId", "context_id") or new_task_id())
    task_id = new_task_id()

    user_message = {
        "messageId": str(_get(msg, "messageId", "message_id") or uuid.uuid4()),
        "contextId": context_id,
        "taskId": task_id,
        "role": str(_get(msg, "role") or "ROLE_USER"),
        "parts": parts,
    }

    task_doc: dict[str, Any] = {
        "id": task_id,
        "contextId": context_id,
        "status": _task_status("TASK_STATE_WORKING", "Research in progress…"),
        "artifacts": [],
        "history": [user_message],
        "metadata": {},
    }
    await store.save(task_doc)
    logger.info("task %s started for query len=%s", task_id, len(user_text))

    if return_immediately:
        _schedule_bg(_run_and_finalize(task_id, context_id, user_text, kb))
        return {"task": task_doc}

    await _run_and_finalize(task_id, context_id, user_text, kb)
    final = await store.get(task_id)
    if not final:
        raise HTTPException(500, "task lost after run")
    return {"task": final}


@app.post("/message:send")
async def message_send(body: dict[str, Any]) -> JSONResponse:
    out = await _handle_send_message(body, None)
    return JSONResponse(out)


@app.post("/{tenant}/message:send")
async def message_send_tenant(tenant: str, body: dict[str, Any]) -> JSONResponse:
    out = await _handle_send_message(body, tenant)
    return JSONResponse(out)


@app.get("/tasks/{task_id}")
@app.get("/{tenant}/tasks/{task_id}")
async def get_task(task_id: str, tenant: str | None = None) -> dict[str, Any]:
    _ = tenant
    t = await store.get(task_id)
    if not t:
        raise HTTPException(404, "task not found")
    return t


@app.get("/tasks")
@app.get("/{tenant}/tasks")
async def list_tasks(
    tenant: str | None = None,
    contextId: str | None = None,
    page_size: int = 50,
) -> dict[str, Any]:
    _ = tenant
    tasks, token = await store.list(context_id=contextId, page_size=page_size)
    return {"tasks": tasks, "nextPageToken": token, "pageSize": page_size, "totalSize": len(tasks)}


@app.post("/tasks/{task_id}:cancel")
@app.post("/{tenant}/tasks/{task_id}:cancel")
async def cancel_task(task_id: str, tenant: str | None = None) -> dict[str, Any]:
    _ = tenant
    t = await store.get(task_id)
    if not t:
        raise HTTPException(404, "task not found")
    store.request_cancel(task_id)
    st = t.get("status") or {}
    state = st.get("state")
    if state in (None, "TASK_STATE_SUBMITTED", "TASK_STATE_WORKING"):
        t["status"] = _task_status("TASK_STATE_CANCELED", "Cancel requested.")
        await store.save(t)
    return t
