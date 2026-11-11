from pathlib import Path
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application & Environment
    PROJECT_NAME: str = "NotebookLM Lite API"
    VERSION: str = "1.5.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # "development", "staging", "production"
    ALLOW_DEMO_FALLBACK: bool = True  # Disabled in production

    # Security & Hardening
    SECRET_KEY: str = "change_me_in_production_min_32_characters_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    RATE_LIMIT_ENABLED: bool = True
    SECURITY_HEADERS_ENABLED: bool = True
    MAX_FILE_PAGE_LIMIT: int = 1500  # DoS mitigation on huge PDFs

    # Database & Connection Pooling
    DATABASE_URL: str = "sqlite+aiosqlite:///./notebooklm.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def resolve_sqlite_path(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("sqlite+aiosqlite:///"):
            raw_path = v.replace("sqlite+aiosqlite:///", "")
            p = Path(raw_path)
            if not p.is_absolute():
                backend_dir = Path(__file__).resolve().parent.parent.parent
                return f"sqlite+aiosqlite:///{(backend_dir / 'notebooklm.db').as_posix()}"
        return v

    # Qdrant Vector DB
    QDRANT_URL: str = ":memory:"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "notebooklm_documents"
    QDRANT_COLLECTION: str = ""

    # Google Gemini
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_CHAT_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"

    # Ingestion & RAG Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RETRIEVAL_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.20

    @property
    def effective_gemini_api_key(self) -> str:
        return self.GOOGLE_API_KEY or self.GEMINI_API_KEY

    @property
    def effective_gemini_chat_model(self) -> str:
        return self.GEMINI_CHAT_MODEL or self.GEMINI_MODEL or "gemini-3.5-flash-lite"

    @property
    def effective_qdrant_collection(self) -> str:
        return self.QDRANT_COLLECTION or self.QDRANT_COLLECTION_NAME or "notebooklm_documents"

    # Storage & AWS S3
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = ""
    S3_ENDPOINT_URL: Union[str, None] = None
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    PRESIGNED_URL_EXPIRE_SECONDS: int = 3600

    # Agent & MCP Settings
    AGENT_WORKFLOW_ENABLED: bool = True
    AGENT_MAX_RETRIES: int = 2
    MCP_SERVER_NAME: str = "notebooklm-mcp"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=[
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env",
        ],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def upload_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()

