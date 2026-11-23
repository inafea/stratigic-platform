"""Application settings loaded from environment variables / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "github"
    llm_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    llm_base_url: str = "https://models.inference.ai.azure.com"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.7

    database_url: str = "sqlite:///./mustashar.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
