from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SRA_",
        env_file=(".env", "agent/.env"),
        extra="ignore",
    )

    base_url: str = "http://127.0.0.1:8080"
    host: str = "0.0.0.0"
    port: int = 8080
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "SRA_OPENAI_API_KEY"),
    )
    openai_model: str = "gpt-4o-mini"
    tavily_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TAVILY_API_KEY", "SRA_TAVILY_API_KEY"),
    )
    # ── Latency budget ────────────────────────────────────────────────────────
    # Total wall budget for one research call. The engine subdivides this
    # across plan/act/reflect/synthesize stages instead of giving the entire
    # budget to a single tool. See ``stage_budget`` for the split.
    research_timeout_sec: int = 90
    # Hard share of total budget reserved for synthesis (LLM generation).
    # Plan/reflect take small fixed amounts; act/deep_web get the remainder.
    synthesize_budget_share: float = 0.30
    plan_budget_sec: float = 6.0
    reflect_budget_sec: float = 4.0

    max_web_results: int = 5
    max_arxiv_results: int = 5
    max_wikipedia_results: int = 3
    max_reflection_rounds: int = 2
    search_retry_attempts: int = 3
    search_retry_delay_sec: float = 0.6
    tool_agent_max_iterations: int = 10
    # Deep web research (Tavily advanced + fetch + relevance + refine loop)
    # Tightened from 3×18s=54s → 2×10s=20s so it fits inside the act-stage
    # budget without starving synthesis.
    deep_web_max_iterations: int = 2
    deep_web_urls_per_iteration: int = 5
    deep_web_min_relevance: float = 0.45
    deep_web_good_enough: float = 0.72
    deep_web_min_accepted: int = 2
    deep_web_max_content_chars: int = 12000
    deep_web_fetch_timeout_sec: float = 10.0
    tavily_search_depth: str = "advanced"  # basic | advanced
    log_level: str = "INFO"

    # ── Governance toggles ────────────────────────────────────────────────────
    safety_enabled: bool = True
    pii_masking_enabled: bool = True
    citation_validation_enabled: bool = True
    # Drop synthesized claims whose URL is not present in the evidence pool.
    citation_strict_mode: bool = False

    # ── Circuit breakers (per external dependency) ────────────────────────────
    # Trip after N consecutive failures; stay open for cooldown_sec.
    breaker_fail_threshold: int = 5
    breaker_cooldown_sec: float = 30.0

    # ── In-memory KB retriever ────────────────────────────────────────────────
    # When the A2A caller passes raw KB chunks, we run BM25 over them and pick
    # the top-K most relevant to the query before they reach the LLM. This
    # avoids dumping irrelevant context into the prompt and matches the
    # platform-api RAG behavior.
    kb_retriever_enabled: bool = True
    kb_retriever_top_k: int = 8

    # ── DIA bridge ────────────────────────────────────────────────────────────
    # Optional. When set, SRA can hand off long extracted documents to the
    # Document Intelligence Agent over A2A. None disables the bridge.
    dia_a2a_base_url: str | None = None
    dia_a2a_timeout_sec: float = 30.0

    # Langfuse observability
    langfuse_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("LANGFUSE_ENABLED", "SRA_LANGFUSE_ENABLED"),
    )
    langfuse_host: str = Field(
        default="http://localhost:3001",
        validation_alias=AliasChoices("LANGFUSE_HOST", "SRA_LANGFUSE_HOST"),
    )
    langfuse_public_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_PUBLIC_KEY", "SRA_LANGFUSE_PUBLIC_KEY"),
    )
    langfuse_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_SECRET_KEY", "SRA_LANGFUSE_SECRET_KEY"),
    )
    langfuse_sample_rate: float = Field(
        default=1.0,
        validation_alias=AliasChoices("LANGFUSE_SAMPLE_RATE", "SRA_LANGFUSE_SAMPLE_RATE"),
    )
    langfuse_release: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_RELEASE", "SRA_LANGFUSE_RELEASE"),
    )
    service_name: str = "strategic-research-agent"


settings = Settings()
