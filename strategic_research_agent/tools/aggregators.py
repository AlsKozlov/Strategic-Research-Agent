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


_CATALOG: tuple[AggregatorSite, ...] = (
    # ── Software reviews & comparisons ──────────────────────────────────────
    AggregatorSite(
        id="g2",
        name="G2",
        domains=("g2.com",),
        tags=frozenset({"compare", "vendors", "software", "b2b", "reviews"}),
        note="Software reviews & comparisons",
    ),
    AggregatorSite(
        id="capterra",
        name="Capterra",
        domains=("capterra.com",),
        tags=frozenset({"compare", "vendors", "software", "reviews"}),
    ),
    AggregatorSite(
        id="trustradius",
        name="TrustRadius",
        domains=("trustradius.com",),
        tags=frozenset({"compare", "vendors", "software", "reviews", "b2b"}),
        note="Verified B2B software reviews",
    ),
    AggregatorSite(
        id="getapp",
        name="GetApp",
        domains=("getapp.com",),
        tags=frozenset({"compare", "vendors", "software", "reviews"}),
    ),
    AggregatorSite(
        id="stackshare",
        name="StackShare",
        domains=("stackshare.io",),
        tags=frozenset({"compare", "technology", "software", "open_source"}),
        note="Tech stacks used by real companies",
    ),
    AggregatorSite(
        id="alternativeto",
        name="AlternativeTo",
        domains=("alternativeto.net",),
        tags=frozenset({"compare", "software", "vendors"}),
        note="Find alternatives to any software",
    ),
    # ── Analyst / enterprise research ───────────────────────────────────────
    AggregatorSite(
        id="gartner",
        name="Gartner",
        domains=("gartner.com",),
        tags=frozenset({"compare", "enterprise", "vendors", "analyst", "market"}),
        note="Magic Quadrant, Peer Insights",
    ),
    AggregatorSite(
        id="forrester",
        name="Forrester",
        domains=("forrester.com",),
        tags=frozenset({"market", "industry", "technology", "analyst", "compare"}),
        note="B2B technology analyst, Wave reports",
    ),
    AggregatorSite(
        id="idc",
        name="IDC",
        domains=("idc.com",),
        tags=frozenset({"market", "industry", "technology", "analyst"}),
        note="IT market share and forecasts",
    ),
    # ── Market research & statistics ────────────────────────────────────────
    AggregatorSite(
        id="statista",
        name="Statista",
        domains=("statista.com",),
        tags=frozenset({"market", "statistics", "industry"}),
    ),
    AggregatorSite(
        id="euromonitor",
        name="Euromonitor",
        domains=("euromonitor.com",),
        tags=frozenset({"market", "industry"}),
    ),
    AggregatorSite(
        id="grandviewresearch",
        name="Grand View Research",
        domains=("grandviewresearch.com",),
        tags=frozenset({"market", "industry", "statistics"}),
        note="Market sizing reports, free executive summaries",
    ),
    AggregatorSite(
        id="mordorintelligence",
        name="Mordor Intelligence",
        domains=("mordorintelligence.com",),
        tags=frozenset({"market", "industry"}),
        note="Market research reports",
    ),
    AggregatorSite(
        id="marketsandmarkets",
        name="MarketsandMarkets",
        domains=("marketsandmarkets.com",),
        tags=frozenset({"market", "industry", "technology"}),
        note="B2B tech market TAM estimates",
    ),
    AggregatorSite(
        id="ibisworld",
        name="IBISWorld",
        domains=("ibisworld.com",),
        tags=frozenset({"market", "industry", "statistics"}),
        note="Industry reports and market share",
    ),
    AggregatorSite(
        id="pewresearch",
        name="Pew Research Center",
        domains=("pewresearch.org",),
        tags=frozenset({"market", "statistics", "general", "news"}),
        note="Demographics, social trends — free and authoritative",
    ),
    AggregatorSite(
        id="ourworldindata",
        name="Our World in Data",
        domains=("ourworldindata.org",),
        tags=frozenset({"market", "statistics", "general"}),
        note="Long-run global data — free and citable",
    ),
    # ── Consulting / strategy reports ───────────────────────────────────────
    AggregatorSite(
        id="mckinsey",
        name="McKinsey & Company",
        domains=("mckinsey.com",),
        tags=frozenset({"market", "strategy", "industry", "consulting"}),
        note="McKinsey Global Institute reports",
    ),
    AggregatorSite(
        id="bcg",
        name="BCG",
        domains=("bcg.com",),
        tags=frozenset({"market", "strategy", "industry", "consulting"}),
        note="BCG strategy reports",
    ),
    AggregatorSite(
        id="deloitte",
        name="Deloitte Insights",
        domains=("deloitte.com",),
        tags=frozenset({"market", "industry", "consulting", "regulatory"}),
    ),
    AggregatorSite(
        id="pwc",
        name="PwC",
        domains=("pwc.com",),
        tags=frozenset({"market", "industry", "consulting", "finance", "regulatory"}),
    ),
    AggregatorSite(
        id="accenture",
        name="Accenture",
        domains=("accenture.com",),
        tags=frozenset({"market", "technology", "consulting"}),
    ),
    AggregatorSite(
        id="hbr",
        name="Harvard Business Review",
        domains=("hbr.org",),
        tags=frozenset({"strategy", "market", "management", "consulting"}),
        note="Strategy and management insights",
    ),
    # ── Company & startup data ───────────────────────────────────────────────
    AggregatorSite(
        id="sec",
        name="SEC EDGAR",
        domains=("sec.gov",),
        tags=frozenset({"company", "filings", "finance", "regulatory", "investment"}),
    ),
    AggregatorSite(
        id="macrotrends",
        name="Macrotrends",
        domains=("macrotrends.net",),
        tags=frozenset({"company", "finance", "investment"}),
        note="Parsed historical financials from SEC data",
    ),
    AggregatorSite(
        id="crunchbase",
        name="Crunchbase",
        domains=("crunchbase.com",),
        tags=frozenset({"company", "startup", "funding", "investment"}),
    ),
    AggregatorSite(
        id="pitchbook",
        name="PitchBook",
        domains=("pitchbook.com",),
        tags=frozenset({"company", "startup", "funding", "investment", "pe", "vc"}),
        note="Private company and PE/VC data",
    ),
    AggregatorSite(
        id="cbinsights",
        name="CB Insights",
        domains=("cbinsights.com",),
        tags=frozenset({"market", "startup", "venture", "technology", "investment"}),
    ),
    AggregatorSite(
        id="tracxn",
        name="Tracxn",
        domains=("tracxn.com",),
        tags=frozenset({"startup", "investment", "company"}),
        note="Startup tracking and sector maps",
    ),
    AggregatorSite(
        id="dealroom",
        name="Dealroom",
        domains=("dealroom.co",),
        tags=frozenset({"startup", "investment", "company"}),
        note="European startup ecosystem",
    ),
    AggregatorSite(
        id="linkedin",
        name="LinkedIn",
        domains=("linkedin.com",),
        tags=frozenset({"company", "talent", "people", "startup"}),
        note="Company pages, employee counts",
    ),
    AggregatorSite(
        id="glassdoor",
        name="Glassdoor",
        domains=("glassdoor.com",),
        tags=frozenset({"company", "talent", "culture", "employer"}),
        note="Employee reviews, salaries",
    ),
    AggregatorSite(
        id="similarweb",
        name="SimilarWeb",
        domains=("similarweb.com",),
        tags=frozenset({"company", "market", "technology", "compare"}),
        note="Web traffic and audience data",
    ),
    # ── Startup ecosystem ────────────────────────────────────────────────────
    AggregatorSite(
        id="ycombinator",
        name="Y Combinator",
        domains=("ycombinator.com",),
        tags=frozenset({"startup", "investment", "technology"}),
        note="YC company profiles and startup news",
    ),
    AggregatorSite(
        id="angellist",
        name="Wellfound / AngelList",
        domains=("wellfound.com",),
        tags=frozenset({"startup", "investment", "talent"}),
    ),
    AggregatorSite(
        id="producthunt",
        name="Product Hunt",
        domains=("producthunt.com",),
        tags=frozenset({"product", "startup", "technology", "compare"}),
        note="New product launches",
    ),
    AggregatorSite(
        id="indiehackers",
        name="Indie Hackers",
        domains=("indiehackers.com",),
        tags=frozenset({"product", "startup"}),
        note="Bootstrapped product stories and revenue data",
    ),
    # ── Tech news & community ────────────────────────────────────────────────
    AggregatorSite(
        id="techcrunch",
        name="TechCrunch",
        domains=("techcrunch.com",),
        tags=frozenset({"news", "startup", "technology", "investment"}),
        note="Startup and tech news",
    ),
    AggregatorSite(
        id="venturebeat",
        name="VentureBeat",
        domains=("venturebeat.com",),
        tags=frozenset({"news", "technology", "ai", "startup"}),
        note="AI and tech news",
    ),
    AggregatorSite(
        id="wired",
        name="Wired",
        domains=("wired.com",),
        tags=frozenset({"news", "technology", "culture"}),
    ),
    AggregatorSite(
        id="arstechnica",
        name="Ars Technica",
        domains=("arstechnica.com",),
        tags=frozenset({"news", "technology", "open_source"}),
        note="Deep technical reporting",
    ),
    AggregatorSite(
        id="theverge",
        name="The Verge",
        domains=("theverge.com",),
        tags=frozenset({"news", "technology", "product"}),
        note="Consumer tech, product launches",
    ),
    AggregatorSite(
        id="github",
        name="GitHub",
        domains=("github.com",),
        tags=frozenset({"technology", "academic", "open_source", "compare"}),
        note="Open-source projects, adoption signals",
    ),
    AggregatorSite(
        id="hackernews",
        name="Hacker News",
        domains=("news.ycombinator.com",),
        tags=frozenset({"technology", "startup", "community", "news"}),
        note="Tech community: Show HN, launches, debates",
    ),
    # ── Business & financial news ────────────────────────────────────────────
    AggregatorSite(
        id="bloomberg",
        name="Bloomberg",
        domains=("bloomberg.com",),
        tags=frozenset({"news", "finance", "company", "market", "investment"}),
        note="Financial and business news",
    ),
    AggregatorSite(
        id="reuters",
        name="Reuters",
        domains=("reuters.com",),
        tags=frozenset({"news", "finance", "company", "regulatory"}),
        note="Wire news, financial markets",
    ),
    AggregatorSite(
        id="ft",
        name="Financial Times",
        domains=("ft.com",),
        tags=frozenset({"news", "finance", "market", "company", "strategy"}),
    ),
    AggregatorSite(
        id="wsj",
        name="Wall Street Journal",
        domains=("wsj.com",),
        tags=frozenset({"news", "finance", "market", "company"}),
    ),
    AggregatorSite(
        id="businessinsider",
        name="Business Insider",
        domains=("businessinsider.com",),
        tags=frozenset({"news", "finance", "technology", "startup"}),
    ),
    AggregatorSite(
        id="economist",
        name="The Economist",
        domains=("economist.com",),
        tags=frozenset({"news", "market", "strategy", "regulatory"}),
        note="Macro trends, country analysis",
    ),
    AggregatorSite(
        id="seekingalpha",
        name="Seeking Alpha",
        domains=("seekingalpha.com",),
        tags=frozenset({"company", "finance", "investment"}),
        note="Equity analysis, earnings summaries",
    ),
    AggregatorSite(
        id="investopedia",
        name="Investopedia",
        domains=("investopedia.com",),
        tags=frozenset({"finance", "general", "market"}),
        note="Finance terminology and frameworks",
    ),
    # ── Academic papers ──────────────────────────────────────────────────────
    AggregatorSite(
        id="arxiv",
        name="arXiv",
        domains=("arxiv.org",),
        tags=frozenset({"academic", "papers", "ml", "cs", "technology"}),
    ),
    AggregatorSite(
        id="semanticscholar",
        name="Semantic Scholar",
        domains=("semanticscholar.org",),
        tags=frozenset({"academic", "papers"}),
    ),
    AggregatorSite(
        id="ssrn",
        name="SSRN",
        domains=("ssrn.com",),
        tags=frozenset({"academic", "papers", "finance", "economics", "regulatory"}),
        note="Social science preprints — finance, economics, law",
    ),
    AggregatorSite(
        id="researchgate",
        name="ResearchGate",
        domains=("researchgate.net",),
        tags=frozenset({"academic", "papers"}),
        note="Author-uploaded papers",
    ),
    # ── General reference ────────────────────────────────────────────────────
    AggregatorSite(
        id="wikipedia",
        name="Wikipedia",
        domains=("en.wikipedia.org",),
        tags=frozenset({"general", "academic", "company", "market", "technology", "background"}),
        note="Background facts, overviews — use early for context",
    ),
    AggregatorSite(
        id="britannica",
        name="Britannica",
        domains=("britannica.com",),
        tags=frozenset({"general", "background"}),
        note="Editorially controlled — good for definitions",
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

    # Comparison / vendor
    if any(
        x in q
        for x in (" vs ", " versus ", "compare ", "comparison", "vendor", "alternatives", "snowflake", "databricks")
    ):
        return "compare"

    # Academic / research papers
    if any(
        x in q
        for x in ("arxiv", "paper", "research paper", "citation", "transformer", "neural", "benchmark", "preprint", "journal")
    ):
        return "academic"

    # Market sizing / industry
    if any(
        x in q
        for x in ("market size", "tam", "cagr", "industry report", "market forecast", "market research", "total addressable")
    ):
        return "market"

    # Investment / VC / PE
    if any(
        x in q
        for x in ("venture capital", " vc ", " pe ", "private equity", "funding round", "series a", "series b", "investors", "portfolio", "valuation", "ipo", "acquisition")
    ):
        return "investment"

    # Startup analysis
    if any(
        x in q
        for x in ("startup", "early-stage", "pre-seed", "seed round", "founder", "pitch deck", "yc ", "y combinator")
    ):
        return "startup"

    # Product / idea validation
    if any(
        x in q
        for x in ("product idea", "validate", "validation", "saas idea", "product launch", "icp", "customer segment", "plg", "product-led", "roadmap")
    ):
        return "product"

    # Technology / engineering
    if any(
        x in q
        for x in ("open source", "github", "framework", "library", "tech stack", "kubernetes", "docker", "api ", "sdk ", "llm ", "vector db", "embedding")
    ):
        return "technology"

    # Regulatory / compliance
    if any(
        x in q
        for x in ("regulation", "compliance", "gdpr", "hipaa", "sec filing", "legal", "policy", "lawsuit", "fda", "regulatory")
    ):
        return "regulatory"

    # Talent / HR
    if any(
        x in q
        for x in ("hiring", "talent market", "salaries", "compensation", "headcount", "layoffs", "remote work", "glassdoor")
    ):
        return "talent"

    # Company analysis (broad)
    if any(
        x in q
        for x in ("company", "analyze ", "analysis of", "10-k", "10k", "revenue", "m&a", "earnings", "annual report", "executive")
    ):
        return "company"

    # Market / industry (broad)
    if any(x in q for x in ("market", "industry", "forecast", "sector", "landscape")):
        return "market"

    # News / recent events
    if any(
        x in q
        for x in ("news", "latest", "recent", "announced", "2024", "2025", "2026", "today", "this week", "last month")
    ):
        return "news"

    return "general"


_ID_MAP: dict[str, AggregatorSite] = {s.id: s for s in _CATALOG}


def select_aggregators(task_type: str, query: str, max_domains: int = 4) -> list[str]:
    """Return up to `max_domains` hostnames to pass to Tavily `include_domains`."""
    _ = query
    tt = (task_type or "general").lower()

    def _pick(*ids: str) -> list[str]:
        domains: list[str] = []
        for sid in ids:
            site = _ID_MAP.get(sid)
            if site:
                for d in site.domains:
                    if d not in domains:
                        domains.append(d)
            if len(domains) >= max_domains:
                break
        return domains[:max_domains]

    if tt == "compare":
        return _pick("g2", "trustradius", "capterra", "stackshare", "gartner", "alternativeto")
    if tt == "academic":
        return _pick("arxiv", "semanticscholar", "ssrn", "researchgate")
    if tt == "market":
        return _pick("statista", "grandviewresearch", "mordorintelligence", "cbinsights", "idc", "euromonitor")
    if tt == "company":
        return _pick("sec", "crunchbase", "macrotrends", "bloomberg", "cbinsights", "seekingalpha")
    if tt == "investment":
        return _pick("crunchbase", "pitchbook", "cbinsights", "bloomberg", "tracxn", "dealroom")
    if tt == "startup":
        return _pick("crunchbase", "techcrunch", "ycombinator", "cbinsights", "producthunt", "hackernews")
    if tt == "product":
        return _pick("producthunt", "g2", "trustradius", "hackernews", "indiehackers", "capterra")
    if tt == "technology":
        return _pick("github", "stackshare", "arxiv", "hackernews", "venturebeat", "arstechnica")
    if tt == "regulatory":
        return _pick("sec", "ssrn", "reuters", "deloitte", "pwc", "economist")
    if tt == "talent":
        return _pick("glassdoor", "linkedin", "seekingalpha", "businessinsider")
    if tt == "news":
        return _pick("bloomberg", "reuters", "techcrunch", "businessinsider", "economist")
    if tt == "general":
        return _pick("wikipedia", "crunchbase", "statista", "techcrunch")

    return _pick("wikipedia", "crunchbase", "statista", "techcrunch")
