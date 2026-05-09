"""External entrypoints: A2A (HTTP), MCP, CLI."""

from strategic_research_agent.interfaces.a2a import app
from strategic_research_agent.interfaces.cli import run_a2a, run_mcp
from strategic_research_agent.interfaces.mcp import mcp

__all__ = ["app", "mcp", "run_a2a", "run_mcp"]
