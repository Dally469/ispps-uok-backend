from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ispps"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expires_minutes: int = 10080  # 7 days
    jwt_algorithm: str = "HS256"

    model_artifact_path: str = str(Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "model.joblib")

    # ── Frontend URL — used to build links inside emails ─────────────────────
    frontend_base_url: str = "http://localhost:3000"

    # ── SMTP — set these in .env to enable outbound email ────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: str = ""    # e.g. you@gmail.com
    smtp_password: str = ""    # Gmail app password (no spaces)
    smtp_from_name: str = "ISPPS"
    smtp_from_email: str = ""  # defaults to smtp_username if empty

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
