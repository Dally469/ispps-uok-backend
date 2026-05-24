from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ispps"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expires_minutes: int = 10080  # 7 days
    jwt_algorithm: str = "HS256"

    model_artifact_path: str = str(Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "model.joblib")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
