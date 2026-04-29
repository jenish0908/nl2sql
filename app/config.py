from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    groq_api_key: str = ""
    database_url: str = "postgresql+asyncpg://nl2sql:nl2sql@postgres:5432/nl2sql_db"
    sync_database_url: str = "postgresql://nl2sql:nl2sql@postgres:5432/nl2sql_db"
    groq_model: str = "llama-3.3-70b-versatile"
    max_result_rows: int = 100
    max_self_corrections: int = 2

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
