"""Synthesize node: final Markdown report from evidence."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.utils.openai_client import AsyncOpenAI
from strategic_research_agent.workflow.nodes.evidence import evidence_digest
from strategic_research_agent.workflow.state import ResearchState

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client

_TASK_SECTIONS: dict[str, str] = {
    "market": (
        "## Market Overview\n(size, CAGR, key segments, geographic breakdown)\n\n"
        "## Key Players & Competitive Landscape\n(market share, positioning)\n\n"
        "## Growth Drivers & Trends\n\n"
        "## Barriers & Risks\n"
    ),
    "company": (
        "## Company Overview\n(business model, products, revenue, headcount)\n\n"
        "## Financial Performance\n(revenue trend, profitability, key metrics)\n\n"
        "## Products & Strategy\n\n"
        "## Competitive Position\n\n"
        "## Risks & Challenges\n"
    ),
    "compare": (
        "## Comparison Matrix\n(feature table: rows = criteria, columns = vendors)\n\n"
        "## Strengths & Weaknesses per Vendor\n\n"
        "## Pricing & Licensing\n\n"
        "## Lock-in Risks\n\n"
        "## Recommendation\n(which option fits which use case)\n"
    ),
    "investment": (
        "## Deal / Funding Overview\n(rounds, investors, valuations)\n\n"
        "## Market Opportunity\n\n"
        "## Business Model & Unit Economics\n\n"
        "## Competitive Moat\n\n"
        "## Risks\n"
    ),
    "startup": (
        "## Company Overview\n(founding, team, product)\n\n"
        "## Funding & Investors\n\n"
        "## Market & Traction\n\n"
        "## Competitive Landscape\n\n"
        "## Risks\n"
    ),
    "product": (
        "## Product / Idea Summary\n\n"
        "## Market Validation\n(TAM, existing demand signals)\n\n"
        "## Competitive Analysis\n\n"
        "## Target ICP\n\n"
        "## Risks & Challenges\n"
    ),
    "technology": (
        "## Technology Overview\n(what it is, how it works)\n\n"
        "## Ecosystem & Adoption\n(GitHub stars, community, companies using it)\n\n"
        "## Alternatives & Trade-offs\n\n"
        "## Maturity & Production Readiness\n"
    ),
    "regulatory": (
        "## Regulatory Context\n(which agencies, frameworks, jurisdictions)\n\n"
        "## Key Requirements & Obligations\n\n"
        "## Recent Developments\n\n"
        "## Compliance Implications\n"
    ),
    "talent": (
        "## Talent Market Overview\n(supply, demand, hot roles)\n\n"
        "## Salary Benchmarks\n\n"
        "## Geographic Distribution\n\n"
        "## Hiring Trends\n"
    ),
    "academic": (
        "## Research Landscape\n(key papers, authors, institutions)\n\n"
        "## Key Methods & Findings\n\n"
        "## Open Problems\n\n"
        "## Practical Applications\n"
    ),
    "news": (
        "## Recent Developments\n(chronological, most recent first)\n\n"
        "## Context & Background\n\n"
        "## Implications\n"
    ),
}

_DEFAULT_SECTIONS = (
    "## Overview\n\n"
    "## Key Findings\n\n"
    "## Analysis\n\n"
    "## Risks & Caveats\n"
)

_CONFIDENCE_RE = re.compile(r"\*\*Confidence:\*\*\s*(High|Medium|Low)", re.I)


def _infer_confidence(text: str, evidence_count: int) -> str:
    """Provisional label only — the engine re-scores via score_confidence()
    after the graph runs (see governance.confidence). This stays as a soft
    hint so the synthesized markdown still ends with a Confidence line even
    when the LLM didn't include one.
    """
    m = _CONFIDENCE_RE.search(text)
    if m:
        return m.group(1).capitalize()
    if evidence_count >= 10:
        return "High"
    if evidence_count >= 4:
        return "Medium"
    return "Low"


async def synthesize_node(state: ResearchState) -> dict[str, Any]:
    q = state.get("query") or ""
    kb = state.get("kb_context") or []
    evidence = state.get("evidence") or []
    digest = evidence_digest(evidence, limit=22000)
    plan_steps = state.get("plan_steps") or []
    task_type = (state.get("task_type") or "general").lower()
    reflection_notes = state.get("reflection_notes") or ""
    today = date.today().isoformat()

    if not settings.openai_api_key:
        lines = [
            "# Strategic research report",
            "",
            "## Plan (PAR)",
            *[f"- {p}" for p in plan_steps],
            "",
            "## Evidence digest",
            digest or "(no evidence retrieved)",
            "",
        ]
        if kb:
            lines += ["## KB context", *[f"- {s[:800]}" for s in kb], ""]
        lines += [
            "## Confidence",
            "Low — set OPENAI_API_KEY for full synthesis.",
        ]
        return {
            "report_markdown": "\n".join(lines),
            "confidence": "Low",
            "caveats": [
                "No LLM synthesis.",
                "Set OPENAI_API_KEY for full narrative and recommendations.",
            ],
            "tools_used": (state.get("tools_used") or []) + ["synthesize_fallback"],
        }

    client = _get_openai_client()

    task_sections = _TASK_SECTIONS.get(task_type, _DEFAULT_SECTIONS)

    system = (
        f"You are Strategic Research Agent — an expert analytical writer. Today's date: {today}.\n\n"
        "Write a rigorous, data-driven Markdown research report. "
        "Cite every factual claim with a markdown link [source title](url) from the evidence. "
        "Flag any information older than 2 years as potentially outdated.\n\n"
        "## Required report structure:\n\n"
        "### Executive Summary\n"
        "(3-5 bullet points: key insight, market position, bottom-line recommendation)\n\n"
        f"{task_sections}\n"
        "## Risks & Data Gaps\n"
        "(paywalled sources, recency issues, conflicting data, missing evidence)\n\n"
        "## Strategic Recommendations\n"
        "(actionable next steps, prioritized by impact)\n\n"
        "## Sources\n"
        "(numbered list of all cited URLs)\n\n"
        "End with exactly:\n"
        "**Confidence:** High | Medium | Low\n"
        "**Caveats:** (bullet list)\n\n"
        "Rules:\n"
        "- Be specific: use numbers, dates, company names — no vague platitudes\n"
        "- If evidence is insufficient for a section, say so explicitly rather than making things up\n"
        "- Keep Executive Summary tight and actionable (3-5 bullets max)\n"
        "- Note when sources are behind paywalls or when snippets may be truncated"
    )

    user_payload: dict[str, Any] = {
        "query": q,
        "today": today,
        "task_type": task_type,
        "plan_steps": plan_steps,
        "evidence_digest": digest,
    }
    if kb:
        user_payload["kb_context"] = [s[:2000] for s in kb[:8]]
    if reflection_notes:
        user_payload["reflection_notes"] = reflection_notes

    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        temperature=0.25,
        max_tokens=6000,
    )
    text = (resp.choices[0].message.content or "").strip()
    confidence = _infer_confidence(text, len(evidence))
    caveats: list[str] = []
    if not evidence:
        caveats.append("No evidence retrieved — results rely entirely on LLM training data.")
    elif len(evidence) < 4:
        caveats.append("Limited evidence retrieved; verify key claims externally.")
    return {
        "report_markdown": text,
        "confidence": confidence,
        "caveats": caveats,
        "tools_used": (state.get("tools_used") or []) + ["synthesize"],
    }
