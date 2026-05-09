"""Curated aggregator / authority sites — selected per task type to narrow Tavily `include_domains`."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AggregatorSite:
    id: str
    name: str
    domains: tuple[str, ...]
    tags: frozenset[str]
    note: str = ""


# Domains are hints for search narrowing; availability of snippets depends on the index.
_CATALOG: tuple[AggregatorSite, ...] = (
    AggregatorSite(
        id="g2",
        name="G2",
        domains=("g2.com",),
        tags=frozenset({"compare", "vendors", "software", "b2b"}),
        note="Software reviews & comparisons",
    ),
    AggregatorSite(
        id="capterra",
        name="Capterra",
        domains=("capterra.com",),
        tags=frozenset({"compare", "vendors", "software"}),
    ),
    AggregatorSite(
        id="gartner_peer",
        name="Gartner Peer Insights",
        domains=("gartner.com",),
        tags=frozenset({"compare", "enterprise", "vendors"}),
    ),
    AggregatorSite(
        id="sec",
        name="SEC EDGAR",
        domains=("sec.gov",),
        tags=frozenset({"company", "filings", "finance"}),
    ),
    AggregatorSite(
        id="crunchbase",
        name="Crunchbase",
        domains=("crunchbase.com",),
        tags=frozenset({"company", "startup", "funding"}),
    ),
    AggregatorSite(
        id="arxiv",
        name="arXiv",
        domains=("arxiv.org",),
        tags=frozenset({"academic", "papers", "ml", "cs"}),
    ),
    AggregatorSite(
        id="semanticscholar",
        name="Semantic Scholar",
        domains=("semanticscholar.org",),
        tags=frozenset({"academic", "papers"}),
    ),
    AggregatorSite(
        id="euromonitor",
        name="Euromonitor",
        domains=("euromonitor.com",),
        tags=frozenset({"market", "industry"}),
    ),
    AggregatorSite(
        id="statista",
        name="Statista",
        domains=("statista.com",),
        tags=frozenset({"market", "statistics", "industry"}),
    ),
    AggregatorSite(
        id="cbinsights",
        name="CB Insights",
        domains=("cbinsights.com",),
        tags=frozenset({"market", "startup", "venture"}),
    ),
)


def list_aggregator_catalog() -> list[dict[str, object]]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "domains": list(s.domains),
            "tags": sorted(s.tags),
            "note": s.note,
        }
        for s in _CATALOG
    ]


def infer_task_type(query: str) -> str:
    q = (query or "").lower()
    if any(
        x in q
        for x in (
            "compare ",
            " vs ",
            " versus ",
            "comparison",
            "vendor",
            "snowflake",
            "databricks",
        )
    ):
        return "compare"
    if any(x in q for x in ("arxiv", "paper", "research paper", "citation", "transformer", "neural")):
        return "academic"
    if any(
        x in q
        for x in (
            "market",
            "market size",
            "tam",
            "industry",
            "forecast",
            "cagr",
        )
    ):
        return "market"
    if any(
        x in q
        for x in (
            "company",
            "analyze ",
            "analysis of",
            "10-k",
            "10k",
            "sec filing",
            "revenue",
            "m&a",
        )
    ):
        return "company"
    return "general"


def select_aggregators(task_type: str, query: str, max_domains: int = 4) -> list[str]:
    """Return up to `max_domains` hostnames to pass to Tavily `include_domains`."""
    _ = query
    tt = (task_type or "general").lower()
    picked: list[AggregatorSite] = []
    if tt == "compare":
        picked = [s for s in _CATALOG if s.id in ("g2", "capterra", "gartner_peer")]
    elif tt == "academic":
        picked = [s for s in _CATALOG if s.id in ("arxiv", "semanticscholar")]
    elif tt == "market":
        picked = [s for s in _CATALOG if s.id in ("statista", "euromonitor", "cbinsights")]
    elif tt == "company":
        picked = [s for s in _CATALOG if s.id in ("sec", "crunchbase", "cbinsights")]
    else:
        picked = [s for s in _CATALOG if s.id in ("g2", "crunchbase", "statista")]

    domains: list[str] = []
    for s in picked:
        for d in s.domains:
            if d not in domains:
                domains.append(d)
            if len(domains) >= max_domains:
                return domains
    return domains[:max_domains]
