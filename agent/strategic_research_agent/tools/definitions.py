"""OpenAI Chat Completions `tools` schema — retrieval agent picks what to call."""

from __future__ import annotations

from typing import Any

OPENAI_RESEARCH_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "General web search (Tavily). Use for news, vendors, companies, markets, "
                "product comparisons, recent events, and broad background."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Focused search query in English or the user's language.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max hits to return (default 5).",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "arxiv_search",
            "description": (
                "Search arXiv for academic papers and preprints (CS, math, physics, q-bio, etc.). "
                "Use when the user needs papers, methods, benchmarks, or scientific evidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords, title fragments, or topics.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max papers (default 5).",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_on_sites",
            "description": (
                "Web search restricted to specific domains (Tavily include_domains). "
                "Use for trusted verticals: e.g. sec.gov (filings), g2.com / capterra.com (software reviews), "
                "crunchbase.com (startups), statista.com (stats), arxiv.org (site mirror), semanticscholar.org."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "1–4 hostnames, e.g. [\"sec.gov\", \"g2.com\"].",
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 5,
                    },
                },
                "required": ["query", "domains"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deep_web_research",
            "description": (
                "Deep web research: Tavily advanced search, optional full-page text extraction, "
                "relevance scoring against the question, automatic query refinement and retries "
                "when pages are weak or off-topic. Use for complex factual questions, product/vendor "
                "comparisons, technical docs, or when snippets are insufficient — prefer this over "
                "plain `web_search` when depth and page-level content matter."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to find out (information need).",
                    },
                    "focus": {
                        "type": "string",
                        "description": "Optional angle: product name, year, region, or constraints.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]
