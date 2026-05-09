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
    research_timeout_sec: int = 60
    max_web_results: int = 5
    max_arxiv_results: int = 5
    max_reflection_rounds: int = 2
    search_retry_attempts: int = 3
    search_retry_delay_sec: float = 0.6
    tool_agent_max_iterations: int = 8
    # Deep web research (Tavily advanced + fetch + relevance + refine loop)
    deep_web_max_iterations: int = 3
    deep_web_urls_per_iteration: int = 5
    deep_web_min_relevance: float = 0.45
    deep_web_good_enough: float = 0.72
    deep_web_min_accepted: int = 2
    deep_web_max_content_chars: int = 12000
    deep_web_fetch_timeout_sec: float = 18.0
    tavily_search_depth: str = "advanced"  # basic | advanced
    log_level: str = "INFO"


settings = Settings()
