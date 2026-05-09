"""Lightweight prompt-injection heuristics for PoC (see docs/governance.md)."""

import re

_SUSPICIOUS = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior)\s+instructions|"
    r"system\s*:\s*|"
    r"you\s+are\s+now\s+|"
    r"disregard\s+(the\s+)?(above|rules)|"
    r"jailbreak)",
    re.I | re.S,
)


def looks_suspicious(user_text: str) -> bool:
    if not user_text or len(user_text) > 32000:
        return True
    return bool(_SUSPICIOUS.search(user_text))
