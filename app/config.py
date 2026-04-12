from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ispps"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expires_minutes: int = 10080  # 7 days
    jwt_algorithm: str = "HS256"
    anthropic_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
