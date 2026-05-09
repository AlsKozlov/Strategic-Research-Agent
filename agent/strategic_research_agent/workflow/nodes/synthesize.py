"""Synthesize node: final Markdown report from evidence."""

from __future__ import annotations

import json
from typing import Any

from strategic_research_agent.config import settings
from strategic_research_agent.workflow.nodes.evidence import evidence_digest
from strategic_research_agent.workflow.state import ResearchState


async def synthesize_node(state: ResearchState) -> dict[str, Any]:
    q = state.get("query") or ""
    kb = state.get("kb_context") or []
    digest = evidence_digest(state.get("evidence") or [], limit=20000)
    plan_steps = state.get("plan_steps") or []

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

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    system = (
        "You are Strategic Research Agent. Write a structured Markdown research report. "
        "Cite sources using markdown links to URLs from the evidence. "
        "Sections: Executive summary, Plan (how it was executed), Findings, "
        "Comparison / alternatives (if relevant), Risks & caveats, Recommendations, Sources. "
        "End with **Confidence:** High/Medium/Low and **Caveats:** bullets."
    )
    user = json.dumps(
        {
            "query": q,
            "plan_steps": plan_steps,
            "kb_context": kb,
            "evidence_digest": digest,
        },
        ensure_ascii=False,
    )
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
        max_tokens=4096,
    )
    text = (resp.choices[0].message.content or "").strip()
    confidence = "Medium"
    caveats: list[str] = []
    if not (state.get("evidence") or []):
        caveats.append("Limited evidence retrieved; verify externally.")
    return {
        "report_markdown": text,
        "confidence": confidence,
        "caveats": caveats,
        "tools_used": (state.get("tools_used") or []) + ["synthesize"],
    }
