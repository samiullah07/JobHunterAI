"""Application configuration loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"
    secret_key: str = "change-me"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    # Verify current model list at console.groq.com/docs/models — swappable via env
    groq_model: str = "llama-3.3-70b-versatile"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384
    llm_daily_call_cap: int = 1000

    database_url: str = "postgresql+asyncpg://jobhunter:jobhunter@localhost:5433/jobhunter"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    match_score_threshold: float = 0.75

    storage_backend: str = "local"
    storage_local_dir: str = "./storage"

    browser_headless: bool = True
    browser_proxy_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
