"""
NotebookLM Lite — Application Configuration
Loaded from environment variables / .env file.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ────────────────────────────────────────────────────
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    allowed_origins: str = "http://localhost:3000"

    # ─── Database ────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/notebooklm"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5433/notebooklm"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ─── Redis ───────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ─── Object Storage ──────────────────────────────────────────────────
    storage_provider: Literal["s3", "minio", "local"] = "local"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "notebooklm-documents"
    s3_use_ssl: bool = False

    # ─── Embedding ───────────────────────────────────────────────────────
    embedding_provider: Literal["openai", "gemini", "local"] = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # ─── LLM ─────────────────────────────────────────────────────────────
    llm_provider: Literal["openai", "gemini"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # ─── Reranker ────────────────────────────────────────────────────────
    reranker_provider: Literal["none", "cohere", "local"] = "none"
    reranker_model: str = "rerank-english-v3.0"
    cohere_api_key: str = ""

    # ─── Chunking ────────────────────────────────────────────────────────
    chunk_token_budget: int = 512
    chunk_overlap_tokens: int = 64

    # ─── Retrieval ───────────────────────────────────────────────────────
    vector_top_k: int = 20
    keyword_top_k: int = 20
    rrf_k: int = 60
    final_top_k: int = 5

    # ─── Upload limits ───────────────────────────────────────────────────
    max_upload_size_mb: int = 50

    @field_validator("allowed_origins")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        return v

    def get_allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
