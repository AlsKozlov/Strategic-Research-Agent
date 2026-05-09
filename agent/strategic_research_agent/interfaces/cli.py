from __future__ import annotations

import os
import sys


def run_a2a() -> None:
    import uvicorn

    from strategic_research_agent.config import settings
    from strategic_research_agent.observability.logging import configure_logging

    configure_logging()
    host = os.environ.get("SRA_HOST", settings.host)
    port = int(os.environ.get("SRA_PORT", str(settings.port)))
    uvicorn.run(
        "strategic_research_agent.interfaces.a2a:app",
        host=host,
        port=port,
        factory=False,
    )


def run_mcp() -> None:
    from strategic_research_agent.interfaces.mcp import mcp
    from strategic_research_agent.observability.logging import configure_logging

    configure_logging()
    transport = "stdio"
    if "--http" in sys.argv:
        transport = "streamable-http"
    mcp.run(transport=transport)
