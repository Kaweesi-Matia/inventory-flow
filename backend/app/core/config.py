"""
Centralized application configuration.

All configuration is loaded from environment variables (see .env.example).
Nothing here should hardcode secrets — this module only defines defaults
for local development.
"""
from functools import lru_cache
from typing import List

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

    APP_NAME: str = "SupplyChainX"
    API_PREFIX: str = "/api"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
