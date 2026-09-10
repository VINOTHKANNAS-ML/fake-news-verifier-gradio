"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "FakeNewsVerifier"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = "sqlite:///./fake_news_verifier.db"

    SERPAPI_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    NEWSAPI_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    ASSEMBLYAI_API_KEY: Optional[str] = None

    ENABLE_MOCK_MODE: bool = False
    MAX_FILE_SIZE_MB: int = 25

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
