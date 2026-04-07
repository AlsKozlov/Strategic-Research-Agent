from __future__ import annotations

import httpx


def get_sync_client(timeout: float = 60.0) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        headers={
            "User-Agent": "StrategicResearchAgent/1.0 (research; +https://github.com/a2aproject/A2A)",
            "Accept": "application/xml, text/xml, application/json, */*",
        },
        follow_redirects=True,
    )


def get_async_client(timeout: float = 60.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        headers={
            "User-Agent": "StrategicResearchAgent/1.0 (research; +https://github.com/a2aproject/A2A)",
            "Accept": "application/xml, text/xml, application/json, */*",
        },
        follow_redirects=True,
    )
