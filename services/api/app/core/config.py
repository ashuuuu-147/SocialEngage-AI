"""Application configuration loaded strictly from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "SocialEngage AI"
    api_base_url: str = "http://localhost:8000"
    web_app_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    # Database & Supabase
    database_url: str = "sqlite:///./socialengage_local.db"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Local Dev Auth & Safe Mock Modes
    dev_auth_bypass: bool = True
    dev_user_id: str = "00000000-0000-0000-0000-000000000001"
    dev_user_email: str = "demo@socialengage.local"
    enable_mock_sources: bool = True

    # AI Provider
    ai_provider: Literal["gemini", "openai_compatible", "mock"] = "mock"
    ai_model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_timeout_seconds: float = 25.0
    ai_daily_user_quota: int = Field(default=50, ge=1, le=1000)

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_webhook_secret: str = ""

    # Internal Worker Security
    internal_job_secret: str = "dev-only-change-me-in-production"
    monitor_default_interval_minutes: int = Field(default=30, ge=5, le=1440)
    monitor_lookback_hours: int = Field(default=48, ge=1, le=720)

    # Optional Platform Credentials
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_access_token: str = ""
    instagram_app_id: str = ""
    instagram_app_secret: str = ""
    instagram_access_token: str = ""

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.app_env == "production":
            if self.dev_auth_bypass:
                raise ValueError("DEV_AUTH_BYPASS must be false in production.")
            if not self.supabase_jwt_secret and not self.supabase_url:
                raise ValueError("Supabase auth configuration is required in production.")
            if self.internal_job_secret == "dev-only-change-me-in-production":
                raise ValueError("INTERNAL_JOB_SECRET must be changed in production.")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
