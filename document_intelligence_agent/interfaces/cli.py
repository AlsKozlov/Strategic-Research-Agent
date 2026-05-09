"""CLI entry points for Document Intelligence Agent."""

from __future__ import annotations


def run_a2a() -> None:
    import uvicorn

    from document_intelligence_agent.config import settings
    from document_intelligence_agent.interfaces.a2a import app

    uvicorn.run(app, host=settings.host, port=settings.port)
