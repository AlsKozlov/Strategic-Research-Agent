"""Task 8 — Multi-Document Synthesis node (map-reduce for large sets)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from document_intelligence_agent.config import settings
from document_intelligence_agent.workflow.state import DocIntelState

logger = logging.getLogger(__name__)


def _heuristic_synthesis(documents: list[str]) -> dict[str, Any]:
    combined = "\n\n---\n\n".join(f"[Doc {i+1}] {doc[:400]}" for i, doc in enumerate(documents))
    return {
        "synthesis": combined,
        "deduplication_notes": [],
        "reconciliation_notes": [],
        "confidence": "low",
        "gaps": ["Set DIA_OPENAI_API_KEY for multi-document synthesis."],
        "evidence": [],
    }


async def _summarize_single(client: Any, doc: str, idx: int) -> str | Exception:
    """Map step: summarize one document. Returns Exception on failure (caller filters)."""
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Summarize the following document in 3–5 sentences, "
                    "preserving all key facts, figures, and conclusions. "
                    "Do not add information not present in the document."
                ),
            },
            {"role": "user", "content": doc[:6000]},
        ],
        temperature=0.1,
        max_tokens=600,
    )
    return f"[Doc {idx + 1}]: " + (resp.choices[0].message.content or "").strip()


async def _llm_synthesize_direct(request: str, documents: list[str]) -> dict[str, Any]:
    """Direct synthesis for small doc sets (≤ threshold)."""
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()
    doc_block = "\n\n".join(
        f"<document index=\"{i + 1}\">\n{doc[:5000]}\n</document>"
        for i, doc in enumerate(documents)
    )
    system = (
        "You are a synthesis specialist. Combine the following documents into a unified coherent narrative.\n"
        "Rules:\n"
        "  - Remove duplication: present each fact once\n"
        "  - Reconcile differences: note where documents agree or conflict\n"
        "  - Preserve all unique insights from every document\n"
        "  - Cite document numbers (e.g. [Doc 2]) for specific claims\n\n"
        "After the synthesis add:\n"
        "  Deduplication notes: what was merged\n"
        "  Reconciliation notes: where documents disagreed and how resolved\n"
        "  Confidence: high | medium | low\n"
        "  Gaps: missing information"
    )
    user = f"Request: {request}\n\nDocuments:\n{doc_block}"
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=3000,
    )
    return _parse_synthesis_text((resp.choices[0].message.content or "").strip(), documents)


async def _llm_synthesize_map_reduce(request: str, documents: list[str]) -> dict[str, Any]:
    """Map-reduce synthesis for larger doc sets."""
    from document_intelligence_agent.utils.llm import get_llm_client

    client = get_llm_client()

    # Map: summarize all docs in parallel; tolerate partial failures
    raw_results = await asyncio.gather(
        *[_summarize_single(client, doc, i) for i, doc in enumerate(documents)],
        return_exceptions=True,
    )
    summaries = [r for r in raw_results if isinstance(r, str)]
    failed = [i for i, r in enumerate(raw_results) if isinstance(r, Exception)]
    if failed:
        logger.warning("map-reduce: %d doc(s) failed summarisation: %s", len(failed), failed)
    if not summaries:
        return _heuristic_synthesis(documents)
    combined_summaries = "\n\n".join(summaries)

    # Reduce: synthesize the summaries
    system = (
        "You are a synthesis specialist. You have individual document summaries. "
        "Combine them into a single unified coherent narrative.\n"
        "  - Eliminate redundancy\n"
        "  - Reconcile any conflicting points\n"
        "  - Cite document numbers for specific claims\n\n"
        "After the synthesis add:\n"
        "  Deduplication notes: what was merged\n"
        "  Reconciliation notes: where documents disagreed\n"
        "  Confidence: high | medium | low\n"
        "  Gaps: missing information"
    )
    user = f"Request: {request}\n\nDocument summaries:\n{combined_summaries}"
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=3000,
    )
    return _parse_synthesis_text((resp.choices[0].message.content or "").strip(), documents)


def _parse_synthesis_text(text: str, documents: list[str]) -> dict[str, Any]:
    confidence = "medium"
    gaps: list[str] = []
    dedup_notes: list[str] = []
    recon_notes: list[str] = []
    synthesis_lines: list[str] = []
    current = "synthesis"

    for line in text.splitlines():
        ll = line.strip().lower()
        if ll.startswith("deduplication notes"):
            current = "dedup"
            continue
        if ll.startswith("reconciliation notes"):
            current = "recon"
            continue
        if ll.startswith("confidence:"):
            val = line.split(":", 1)[-1].strip().lower()
            if val in ("high", "medium", "low"):
                confidence = val
            continue
        if ll.startswith("gaps:"):
            current = "gaps"
            continue
        if current == "synthesis":
            synthesis_lines.append(line)
        elif current == "dedup" and line.strip().startswith("-"):
            dedup_notes.append(line.strip().lstrip("- ").strip())
        elif current == "recon" and line.strip().startswith("-"):
            recon_notes.append(line.strip().lstrip("- ").strip())
        elif current == "gaps" and line.strip().startswith("-"):
            gap = line.strip().lstrip("- ").strip()
            if gap.lower() != "none":
                gaps.append(gap)

    return {
        "synthesis": "\n".join(synthesis_lines).strip(),
        "deduplication_notes": dedup_notes,
        "reconciliation_notes": recon_notes,
        "confidence": confidence,
        "gaps": gaps,
        "evidence": [{"doc_idx": i, "quote": doc.strip()[:120]} for i, doc in enumerate(documents[:5])],
    }


async def multi_synthesis_node(state: DocIntelState) -> dict[str, Any]:
    request = state.get("request") or ""
    documents = state.get("documents") or []

    if not documents:
        return {"task_result": {"synthesis": "", "deduplication_notes": [], "reconciliation_notes": [], "confidence": "low", "gaps": ["No documents provided."], "evidence": []}}

    if not settings.openai_api_key:
        return {"task_result": _heuristic_synthesis(documents)}

    if len(documents) > settings.multi_synthesis_map_threshold:
        logger.info("multi_synthesis: map-reduce mode, docs=%d", len(documents))
        result = await _llm_synthesize_map_reduce(request, documents)
    else:
        logger.info("multi_synthesis: direct mode, docs=%d", len(documents))
        result = await _llm_synthesize_direct(request, documents)

    logger.info("multi_synthesis: confidence=%s", result.get("confidence"))
    return {"task_result": result}
