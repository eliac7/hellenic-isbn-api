from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "hellenic-isbn-api"
    environment: str = "development"
    log_level: str = "INFO"

    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    cache_ttl_seconds: int = 3600

    nlg_base_url: str = "https://isbn.nlg.gr"
    curl_impersonate: str = "chrome124"

    # Simple in-memory rate limit per process.
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    request_timeout_seconds: float = 12.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
