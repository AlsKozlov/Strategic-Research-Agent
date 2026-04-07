from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DIA_",
        env_file=(".env", "agent/.env"),
        extra="ignore",
    )

    base_url: str = "http://127.0.0.1:8081"
    host: str = "0.0.0.0"
    port: int = 8081

    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "DIA_OPENAI_API_KEY"),
    )
    openai_model: str = "gpt-4o-mini"

    processing_timeout_sec: int = 120
    # Per-document input limits
    max_document_chars: int = 80_000        # ~20k tokens per doc
    max_documents: int = 10
    # conflict_detect pairwise budget: C(10,2) = 45
    conflict_max_pairs: int = 45
    # above this doc count, multi_synthesis uses map-reduce
    multi_synthesis_map_threshold: int = 3

    # ── Governance toggles ────────────────────────────────────────────────────
    safety_enabled: bool = True
    pii_masking_enabled: bool = True
    # Mask PII inside document bodies as well as the request string. Off by
    # default because doc payloads can be large and the redaction may distort
    # downstream extraction.
    pii_mask_documents: bool = False

    # ── Circuit breakers ──────────────────────────────────────────────────────
    breaker_fail_threshold: int = 5
    breaker_cooldown_sec: float = 30.0

    log_level: str = "INFO"

    # Langfuse observability
    langfuse_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("LANGFUSE_ENABLED", "DIA_LANGFUSE_ENABLED"),
    )
    langfuse_host: str = Field(
        default="http://localhost:3001",
        validation_alias=AliasChoices("LANGFUSE_HOST", "DIA_LANGFUSE_HOST"),
    )
    langfuse_public_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_PUBLIC_KEY", "DIA_LANGFUSE_PUBLIC_KEY"),
    )
    langfuse_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_SECRET_KEY", "DIA_LANGFUSE_SECRET_KEY"),
    )
    langfuse_sample_rate: float = Field(
        default=1.0,
        validation_alias=AliasChoices("LANGFUSE_SAMPLE_RATE", "DIA_LANGFUSE_SAMPLE_RATE"),
    )
    langfuse_release: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_RELEASE", "DIA_LANGFUSE_RELEASE"),
    )
    service_name: str = "document-intelligence-agent"


settings = Settings()
