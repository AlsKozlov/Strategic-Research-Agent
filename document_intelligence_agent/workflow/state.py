from __future__ import annotations

from typing import TypedDict


class DocIntelState(TypedDict, total=False):
    """Graph state flowing through all Document Intelligence nodes."""

    # ── Input ────────────────────────────────────────────────────────────────
    request: str            # user instructions / question
    documents: list[str]   # raw text, one entry per document
    doc_meta: list[dict]   # [{filename, source, ...}] parallel to documents

    # Task-specific optional inputs
    output_schema: dict | None   # JSON schema hint for structured_extract
    target_format: str | None    # target format string for template_map
    summary_format: str | None   # executive | bullets | risks | actions

    # ── Task routing ─────────────────────────────────────────────────────────
    task_type: str          # result of classify_node

    # ── Task output ──────────────────────────────────────────────────────────
    task_result: dict       # structured output from the chosen task node

    # ── Final envelope (populated by finalize_node) ───────────────────────
    confidence: str         # high | medium | low
    evidence: list[dict]   # [{doc_idx: int, quote: str}]
    gaps: list[str]        # missing data / caveats

    # ── Error tracking ───────────────────────────────────────────────────────
    errors: list[str]
