from typing import Any, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Career Counseling API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    APP_URL: str = "http://localhost:8000"  # Base URL for internal API calls

    # Database
    DATABASE_URL: str = "postgresql://CHANGE_ME:CHANGE_ME@localhost:5432/career_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 0

    # Redis
    REDIS_URL: Optional[str] = None

    # Security
    SECRET_KEY: str = "test-secret-key-CHANGE-IN-PRODUCTION"  # REQUIRED: Must be set in .env (generate with: openssl rand -hex 32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days

    # OpenAI (用於 Embeddings, Whisper STT, RAG Chat)
    OPENAI_API_KEY: Optional[str] = "sk-test-key-for-ci"  # Override in .env
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    # Gemini / Vertex AI (主要 LLM)
    GEMINI_PROJECT_ID: str = "groovy-iris-473015-h3"
    GEMINI_LOCATION: str = "us-central1"
    GEMINI_CHAT_MODEL: str = "gemini-2.5-flash"  # or "gemini-2.5-flash-lite"

    # LLM Provider Selection
    DEFAULT_LLM_PROVIDER: str = "gemini"  # "openai" or "gemini" - 預設使用 Gemini

    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    SUPABASE_BUCKET: str = "documents"
    STORAGE_TYPE: str = "supabase"

    # RAG Settings
    VECTOR_DIMENSIONS: int = 1536
    DEFAULT_TOP_K: int = 5
    DEFAULT_CHUNK_SIZE: int = 400
    DEFAULT_CHUNK_OVERLAP: int = 80
    MAX_FILE_SIZE_MB: int = 30
    PIPELINE_TIMEOUT_SECONDS: int = 180

    # Application
    ENVIRONMENT: str = "development"
    API_ADMIN_KEY: Optional[str] = None

    # Google Cloud Storage
    GCS_BUCKET: Optional[str] = None
    GCS_PROJECT: Optional[str] = None

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "logs/app.log"

    # File Upload
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_AUDIO_TYPES: List[str] = [".mp3", ".wav", ".m4a", ".aac"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Allow extra fields from .env
        # Parse comma-separated strings for List fields
        env_parse_none_str="null",
    )


settings = Settings()  # type: ignore[call-arg]
