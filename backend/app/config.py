from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"), extra="ignore")

    app_name: str = "Your Health Guide"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'app.db'}"
    checkpoint_db: str = str(BACKEND_DIR / "data" / "checkpoints.db")

    jwt_secret: str = "dev-only-secret-change-me-in-production-please"
    jwt_expire_minutes: int = 60 * 24 * 7
    max_followups: int = 4
    clinic_timezone: str = "America/New_York"
    booking_window_days: int = 14
    cors_origins: str = "http://localhost:5173"
    static_dir: str = str(BACKEND_DIR / "static")
    seed_on_startup: bool = True
    show_demo_accounts: bool = True  # expose seeded demo logins on the login page

    @field_validator("openai_api_key", "jwt_secret", mode="before")
    @classmethod
    def _clean_secret(cls, v):
        # Secrets pasted with surrounding whitespace/quotes (e.g. `"sk-..."`) would otherwise break auth.
        return v.strip().strip('"').strip("'").strip() if isinstance(v, str) else v

    @property
    def demo_mode(self) -> bool:
        return not self.openai_api_key

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith(("postgres://", "postgresql"))

    @property
    def postgres_dsn(self) -> str:
        """Plain libpq DSN (for the LangGraph Postgres checkpointer)."""
        url = self.database_url.replace("postgresql+psycopg://", "postgresql://")
        return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url


@lru_cache
def get_settings() -> Settings:
    return Settings()
