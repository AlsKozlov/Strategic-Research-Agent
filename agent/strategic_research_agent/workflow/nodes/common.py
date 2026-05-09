"""Shared helpers for LangGraph nodes (JSON cleanup, PAR limits)."""

from __future__ import annotations

import re

from strategic_research_agent.config import settings


def max_act_passes() -> int:
    return 1 + int(settings.max_reflection_rounds)


def clean_json_block(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()
