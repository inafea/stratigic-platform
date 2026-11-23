"""Application settings loaded from environment variables / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "github"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-4.1-mini"
    llm_base_url: str = "https://models.github.ai/inference"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.7
    # Claude only: low | medium | high | xhigh | max (empty = model default)
    llm_effort: str = ""

    database_url: str = "sqlite:///./mustashar.db"
    # owner of reports created before accounts existed
    admin_email: str = "admin@localhost"

    # limits apply per client IP to endpoints that call the LLM
    rate_limit: str = "10/minute"
    auth_rate_limit: str = "10/minute"

    # accounts
    session_days: int = 30
    cookie_secure: bool = False  # set true in production (HTTPS)
    # base URL used in links inside emails
    public_url: str = "http://127.0.0.1:8000"

    # Sign in with Google (empty = disabled). Redirect URI: {PUBLIC_URL}/api/auth/google/callback
    google_client_id: str = ""
    google_client_secret: str = ""

    # email: console (log only) | smtp
    mail_backend: str = "console"
    mail_from: str = "Mustashar <no-reply@localhost>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
