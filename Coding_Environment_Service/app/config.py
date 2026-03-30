from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    ALLOWED_HOSTS: str = "*"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/proctordb"
    DATABASE_SYNC_URL: str = "postgresql://user:password@localhost:5432/proctordb"
    AUTO_INIT_DB: bool = True

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Execution Limits ──────────────────────────────────────────────────────
    MAX_EXECUTION_TIME_SECONDS: int = 10
    MAX_MEMORY_MB: int = 256
    MAX_OUTPUT_BYTES: int = 65536          # 64 KB
    MAX_CONCURRENT_EXECUTIONS: int = 50
    EXECUTION_TIMEOUT_BUFFER_SECONDS: int = 2  # extra time before Docker kill

    # ── Supported languages ───────────────────────────────────────────────────
    SUPPORTED_LANGUAGES: List[str] = ["python", "javascript", "java", "cpp", "go", "rust"]

    # ── Docker ────────────────────────────────────────────────────────────────
    DOCKER_NETWORK: str = "none"           # NO network access in sandbox
    SANDBOX_IMAGE_PREFIX: str = "proctor-sandbox"

    # ── Storage ───────────────────────────────────────────────────────────────
    S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"
    LOG_TO_S3: bool = False

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_SUBMISSIONS_PER_MINUTE: int = 5
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
