"""
Central configuration for the AI CCTV backend.

All secrets are pulled from environment variables (or a .env file in dev).
Nothing sensitive should be hard-coded here.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "AI CCTV Monitoring System"
    ENV: str = "development"  # "production" in deployment

    # --- Database ---
    # Local dev default: SQLite file. In production point this at TimescaleDB:
    # e.g. postgresql+psycopg2://user:password@db-host:5432/cctv
    DATABASE_URL: str = "sqlite:///./cctv.db"

    # --- Auth / JWT ---
    # Generate a strong secret in production, e.g.: openssl rand -hex 32
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Account lockout (basic brute-force protection) ---
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    # --- CORS ---
    # Restrict this to your Flutter app's origin(s) in production.
    ALLOWED_ORIGINS: list[str] = ["*"]

    # --- Internal service auth (AI pipeline -> backend, not user-facing) ---
    # Generate with: openssl rand -hex 32. The detection pipeline sends this
    # in an X-Internal-Api-Key header when POSTing confirmed events.
    INTERNAL_API_KEY: str = "CHANGE_ME_PIPELINE_KEY"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
