"""
Centralized application configuration.

All configuration is loaded from environment variables (see .env.example).
Nothing here should hardcode secrets — this module only defines defaults
for local development.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = (
        "postgresql+psycopg2://supplychainx:supplychainx@localhost:5432/supplychainx"
    )

    # JWT
    JWT_SECRET_KEY: str = "dev-only-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Preview deploys on Vercel (https://*.vercel.app)
    CORS_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"

    APP_NAME: str = "SupplyChainX"
    API_PREFIX: str = "/api"

    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        # Render (and Heroku) provide postgres:// ; SQLAlchemy 2 + psycopg2 need postgresql+psycopg2://
        if value.startswith("postgres://"):
            value = "postgresql+psycopg2://" + value[len("postgres://") :]
        elif value.startswith("postgresql://") and "+psycopg2" not in value:
            value = "postgresql+psycopg2://" + value[len("postgresql://") :]
        return value

    @model_validator(mode="after")
    def require_ssl_for_render_external(self):
        url = self.DATABASE_URL
        if "sslmode=" not in url and "render.com" in url:
            self.DATABASE_URL = url + ("&" if "?" in url else "?") + "sslmode=require"
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
