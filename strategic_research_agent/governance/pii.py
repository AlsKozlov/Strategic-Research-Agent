"""PII detection + masking applied at the A2A ingress boundary.

The agent forwards user text to third-party services (Tavily, OpenAI, DDG).
We never want raw PII leaving the trust boundary, so the A2A handler runs
``mask_pii`` on every inbound text part before it reaches the engine.

Patterns are intentionally conservative — we prefer false negatives over
false positives that would mangle legitimate analytical queries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── Regexes ───────────────────────────────────────────────────────────────────
# Order matters: more specific patterns run first so they win on overlap.

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
# E.164-ish or grouped national; require at least 9 digits to dodge years/IDs.
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d[\s\-().]{0,2}){9,15}(?!\w)"
)
# Credit card: 13–19 digits, optionally grouped by spaces or dashes.
_CARD_RE = re.compile(
    r"(?<!\d)(?:\d[ \-]?){13,19}(?!\d)"
)
# IPv4 — quad with each octet 0–255.
_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\b"
)
# IBAN — 2 letters + 2 digits + up to 30 alnum.
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")


@dataclass(frozen=True)
class PIIScanResult:
    masked_text: str
    counts: dict[str, int]

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def _luhn_ok(digits: str) -> bool:
    s = 0
    alt = False
    for ch in reversed(digits):
        if not ch.isdigit():
            continue
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        s += d
        alt = not alt
    return s > 0 and s % 10 == 0


def _mask_card(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    # Avoid masking arbitrary long digit runs (IDs, hashes) — require Luhn.
    if not _luhn_ok(digits):
        return match.group(0)
    return "[CARD]"


def mask_pii(text: str) -> PIIScanResult:
    """Return text with detected PII replaced by ``[KIND]`` placeholders.

    The function is pure and side-effect free; it never raises on malformed
    input. Empty input returns an empty result with zero counts.
    """
    if not text:
        return PIIScanResult(masked_text="", counts={})

    counts: dict[str, int] = {}

    def _sub(name: str, pattern: re.Pattern[str], placeholder: str, body: str) -> str:
        n = 0

        def _repl(_m: re.Match[str]) -> str:
            nonlocal n
            n += 1
            return placeholder

        out = pattern.sub(_repl, body)
        if n:
            counts[name] = counts.get(name, 0) + n
        return out

    out = text
    out = _sub("email", _EMAIL_RE, "[EMAIL]", out)
    out = _sub("iban", _IBAN_RE, "[IBAN]", out)

    # Card requires Luhn validation, so use a custom replace.
    card_hits = 0

    def _card_repl(m: re.Match[str]) -> str:
        nonlocal card_hits
        replacement = _mask_card(m)
        if replacement == "[CARD]":
            card_hits += 1
        return replacement

    out = _CARD_RE.sub(_card_repl, out)
    if card_hits:
        counts["card"] = card_hits

    # IMPORTANT: IPv4 must run BEFORE phone — the phone pattern allows
    # punctuation between digits and would otherwise swallow `1.2.3.4`.
    out = _sub("ipv4", _IPV4_RE, "[IP]", out)
    out = _sub("phone", _PHONE_RE, "[PHONE]", out)

    return PIIScanResult(masked_text=out, counts=counts)


def mask_many(texts: list[str]) -> tuple[list[str], dict[str, int]]:
    """Mask a list of strings, returning masked list and aggregated counts."""
    aggregated: dict[str, int] = {}
    out: list[str] = []
    for t in texts:
        r = mask_pii(t)
        out.append(r.masked_text)
        for k, v in r.counts.items():
            aggregated[k] = aggregated.get(k, 0) + v
    return out, aggregated


__all__ = ["PIIScanResult", "mask_pii", "mask_many"]
