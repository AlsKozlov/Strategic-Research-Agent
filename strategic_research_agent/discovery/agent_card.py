from __future__ import annotations

from strategic_research_agent.config import settings


def build_agent_card() -> dict:
    base = settings.base_url.rstrip("/")
    return {
        "name": "Strategic Research Agent",
        "description": (
            "Multi-step strategic research: markets, companies, vendor comparison, "
            "idea validation, and structured reports with sources and confidence."
        ),
        "supportedInterfaces": [
            {
                "url": base,
                "protocolBinding": "HTTP+JSON",
                "protocolVersion": "1.0",
            }
        ],
        "provider": {
            "url": "https://github.com/a2aproject/A2A",
            "organization": "Strategic Research Agent (PoC)",
        },
        "version": "0.1.0",
        "documentationUrl": "https://github.com/a2aproject/A2A",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "extendedAgentCard": True,
            "extensions": [
                {
                    "uri": "urn:sra:langgraph:par",
                    "description": "Plan–Act–Reflect loop implemented with LangGraph; retrieval via Tavily + arXiv + aggregator-scoped search.",
                    "required": False,
                }
            ],
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id": "topic_research",
                "name": "Research by topic",
                "description": "Collect sources and produce a structured report on a topic or market.",
                "tags": ["research", "market", "analysis"],
                "examples": ["Research AI infrastructure market in EU"],
            },
            {
                "id": "company_analysis",
                "name": "Company analysis",
                "description": "Overview, strategy, market, risks for a named company.",
                "tags": ["company", "competitive"],
                "examples": ["Analyze company Stripe"],
            },
            {
                "id": "vendor_compare",
                "name": "Vendor comparison",
                "description": "Compare vendors/tools with trade-offs and lock-in risks.",
                "tags": ["compare", "vendors"],
                "examples": ["Compare Snowflake vs Databricks"],
            },
            {
                "id": "idea_validation",
                "name": "Product idea validation",
                "description": "Market, competitors, ICP, risks for a product or startup idea.",
                "tags": ["validation", "startup"],
                "examples": ["Evaluate idea: AI platform for document intelligence"],
            },
        ],
    }
