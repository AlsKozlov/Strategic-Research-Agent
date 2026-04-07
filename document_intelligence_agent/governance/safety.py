"""Lightweight prompt-injection and abuse heuristics."""

from __future__ import annotations

import re

from document_intelligence_agent.config import settings

_SUSPICIOUS = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior)\s+instructions|"
    r"system\s*:\s*|"
    r"you\s+are\s+now\s+|"
    r"disregard\s+(the\s+)?(above|rules)|"
    r"jailbreak)",
    re.I | re.S,
)

# Per-document injection check is regex-only (no size limit — docs can be large)
_INJECTION_ONLY = re.compile(_SUSPICIOUS.pattern, re.I | re.S)


def looks_suspicious(text: str) -> bool:
    """Return True if the *request* string looks like prompt injection or abuse."""
    if not text:
        return True
    # Request strings are expected to be short; reject very long ones
    if len(text) > 32_000:
        return True
    return bool(_SUSPICIOUS.search(text))


def document_has_injection(doc: str) -> bool:
    """Return True if a document body contains prompt-injection patterns.

    Size is not checked here — callers already clamp document length via
    settings.max_document_chars before reaching this function.
    """
    if not doc:
        return False
    return bool(_INJECTION_ONLY.search(doc))
