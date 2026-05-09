"""MCP server exposing Strategic Research Agent as tools (stdio or streamable-http)."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from strategic_research_agent.research.engine import run_research
from strategic_research_agent.research.task_store import research_to_artifact_dict
from strategic_research_agent.tools.aggregators import list_aggregator_catalog

mcp = FastMCP("Strategic Research Agent")


@mcp.tool()
def list_research_aggregators() -> str:
    """Return curated aggregator sites (domains/tags) used for scoped Tavily search in PAR."""
    return json.dumps(list_aggregator_catalog(), ensure_ascii=False, indent=2)


@mcp.tool()
async def strategic_research(
    query: str,
    kb_context: str = "",
) -> str:
    """Run multi-step strategic research (web + optional KB snippets) and return structured JSON.

    Use for market/company research, vendor comparison, or idea validation. Pass internal context
    via kb_context when integrating with your knowledge base.
    """
    kb = [kb_context.strip()] if kb_context and kb_context.strip() else []
    result = await run_research(query, kb)
    payload = research_to_artifact_dict(result)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run(transport="stdio")
