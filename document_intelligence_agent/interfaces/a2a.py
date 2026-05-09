"""A2A HTTP interface for Document Intelligence Agent."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from document_intelligence_agent.config import settings
from document_intelligence_agent.discovery.agent_card import build_agent_card
from document_intelligence_agent.governance.pii import mask_many, mask_pii
from document_intelligence_agent.governance.safety import (
    document_has_injection,
    looks_suspicious,
)
from document_intelligence_agent.observability.langfuse_client import (
    flush as flush_langfuse,
    get_langfuse,
)
from document_intelligence_agent.observability.logging import configure_logging
from document_intelligence_agent.processing.engine import DocIntelResult, run_doc_intel
from document_intelligence_agent.processing.task_store import (
    TaskStore,
    new_task_id,
    result_to_artifact_dict,
)

configure_logging()
logger = logging.getLogger(__name__)

# Eagerly initialize Langfuse so misconfiguration surfaces at startup.
get_langfuse()

app = FastAPI(title="Document Intelligence Agent (A2A)")


@app.on_event("shutdown")
async def _flush_observability() -> None:
    flush_langfuse()
store = TaskStore()
_bg_tasks: set[asyncio.Task] = set()

Instrumentator(
    should_group_status_codes=True,
    excluded_handlers=["/.well-known/agent.json", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# ── A2A message helpers ───────────────────────────────────────────────────────

def _get(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _parts_to_documents(parts: list[Any]) -> list[str]:
    """Each text part becomes one document. Non-text parts are skipped."""
    docs: list[str] = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        text = _get(p, "text")
        if isinstance(text, str) and text.strip():
            docs.append(text.strip())
    return docs


def _parse_metadata(
    metadata: dict[str, Any] | None,
) -> tuple[dict | None, str | None, str | None, list[dict]]:
    """Extract optional structured inputs from message metadata."""
    if not metadata:
        return None, None, None, []
    output_schema = _get(metadata, "outputSchema", "output_schema")
    target_format = _get(metadata, "targetFormat", "target_format")
    summary_format = _get(metadata, "summaryFormat", "summary_format")
    raw_meta = _get(metadata, "docMeta", "doc_meta")
    doc_meta: list[dict] = []
    if isinstance(raw_meta, list):
        doc_meta = [d if isinstance(d, dict) else {} for d in raw_meta]
    return (
        output_schema if isinstance(output_schema, dict) else None,
        str(target_format) if target_format else None,
        str(summary_format) if summary_format else None,
        doc_meta,
    )


def _task_status(state: str, text: str | None = None) -> dict[str, Any]:
    msg: dict[str, Any] | None = None
    if text is not None:
        msg = {
            "messageId": str(uuid.uuid4()),
            "role": "ROLE_AGENT",
            "parts": [{"text": text, "mediaType": "text/plain"}],
        }
    return {"state": state, "message": msg}


def _result_to_artifact(result: DocIntelResult) -> dict[str, Any]:
    data = result_to_artifact_dict(
        task_type=result.task_type,
        task_result=result.task_result,
        confidence=result.confidence,
        evidence=result.evidence,
        gaps=result.gaps,
        latency_sec=result.latency_sec,
    )
    return {
        "artifactId": str(uuid.uuid4()),
        "name": f"doc_intel_{result.task_type}",
        "description": f"Document Intelligence output: {result.task_type} (confidence: {result.confidence})",
        "parts": [
            {"mediaType": "application/json", "data": data},
        ],
    }


# ── Background runner ─────────────────────────────────────────────────────────

async def _run_and_finalize(
    task_id: str,
    context_id: str,
    request: str,
    documents: list[str],
    doc_meta: list[dict],
    output_schema: dict | None,
    target_format: str | None,
    summary_format: str | None,
) -> None:
    try:
        if store.is_cancelled(task_id):
            t = await store.get(task_id)
            if t:
                t["status"] = _task_status("TASK_STATE_CANCELED", "Canceled.")
                await store.save(t)
            return

        result = await run_doc_intel(
            request=request,
            documents=documents,
            doc_meta=doc_meta or [],
            output_schema=output_schema,
            target_format=target_format,
            summary_format=summary_format,
        )

        artifact = _result_to_artifact(result)
        summary = (
            f"Completed task '{result.task_type}'. "
            f"Confidence: {result.confidence}. "
            f"Latency: {result.latency_sec:.2f}s. "
            f"See artifact for full output."
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
        logger.info("task %s completed: task_type=%s latency=%.3fs", task_id, result.task_type, result.latency_sec)

    except Exception as exc:
        logger.exception("task %s failed: %s", task_id, exc)
        t = await store.get(task_id)
        if t:
            t["status"] = _task_status("TASK_STATE_FAILED", str(exc))
            await store.save(t)


def _schedule_bg(coro: Any) -> None:
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


# ── A2A endpoints ─────────────────────────────────────────────────────────────

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

    documents = _parts_to_documents(parts)
    if not documents:
        raise HTTPException(400, "No text parts found. Send document text as message parts.")

    # Message layout:
    #   metadata.instruction (optional) — explicit instruction / task description
    #   parts[0]             — instruction (if no metadata.instruction AND len > 1)
    #   parts[1:]            — document bodies
    # Single-part message: the part is treated as the document; task is inferred.
    raw_meta = msg.get("metadata")
    metadata: dict[str, Any] | None = raw_meta if isinstance(raw_meta, dict) else None
    if metadata is None:
        raw_meta = body.get("metadata")
        metadata = raw_meta if isinstance(raw_meta, dict) else None

    output_schema, target_format, summary_format, doc_meta = _parse_metadata(metadata)

    # Resolve request string (instruction)
    explicit_instruction = str((metadata or {}).get("instruction") or "").strip()
    if explicit_instruction:
        request = explicit_instruction
        # All parts are documents
    elif len(documents) >= 2:
        # First part is instruction, remainder are documents
        request = documents[0]
        documents = documents[1:]
    else:
        # Single part: it is the document; use a generic instruction so classify
        # can still infer the task from request+content combined.
        request = documents[0]
        # documents stays unchanged — same text serves as document to process

    # ── Governance: safety + PII at the trust boundary ───────────────────────
    if settings.safety_enabled:
        if looks_suspicious(request):
            logger.warning("rejected suspicious instruction (len=%d)", len(request))
            raise HTTPException(
                status_code=400,
                detail="Request rejected by safety heuristics.",
            )
        injected = [i for i, d in enumerate(documents) if document_has_injection(d)]
        if injected:
            logger.warning("rejected docs with injection at %s", injected)
            raise HTTPException(
                status_code=400,
                detail=f"Documents at index {injected} contain prompt-injection patterns.",
            )

    pii_redactions: dict[str, int] = {}
    if settings.pii_masking_enabled:
        scan = mask_pii(request)
        request = scan.masked_text
        pii_redactions = dict(scan.counts)
        if settings.pii_mask_documents:
            documents, doc_counts = mask_many(documents)
            for k, v in doc_counts.items():
                pii_redactions[k] = pii_redactions.get(k, 0) + v

    cfg = body.get("configuration") or {}
    return_immediately = bool(_get(cfg, "returnImmediately", "return_immediately") or False)

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
        "status": _task_status("TASK_STATE_WORKING", "Processing documents…"),
        "artifacts": [],
        "history": [user_message],
        "metadata": {"pii_redactions": pii_redactions} if pii_redactions else {},
    }
    await store.save(task_doc)
    logger.info("task %s started: docs=%d request_len=%d", task_id, len(documents), len(request))

    coro = _run_and_finalize(
        task_id=task_id,
        context_id=context_id,
        request=request,
        documents=documents,
        doc_meta=doc_meta,
        output_schema=output_schema,
        target_format=target_format,
        summary_format=summary_format,
    )

    if return_immediately:
        _schedule_bg(coro)
        return {"task": task_doc}

    await coro
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
    page_size = min(max(page_size, 1), 200)
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
    if st.get("state") in (None, "TASK_STATE_SUBMITTED", "TASK_STATE_WORKING"):
        t["status"] = _task_status("TASK_STATE_CANCELED", "Cancel requested.")
        await store.save(t)
    return t
