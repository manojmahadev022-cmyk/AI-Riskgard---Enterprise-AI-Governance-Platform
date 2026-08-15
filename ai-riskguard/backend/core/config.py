from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults."""

    PROJECT_NAME: str = "AI RiskGuard"
    VERSION: str = "0.3.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database — SQLite for zero-config local dev; PostgreSQL-ready
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/airiskguard.db"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── AI Provider (optional) ───────────────────────────────────────────────
    # AI_PROVIDER=local     → FallbackProvider (sentence extraction, no LLM)
    # AI_PROVIDER=ollama    → OllamaProvider (requires Ollama running locally)
    AI_PROVIDER: str = "local"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # ── Research / Source Retrieval Settings ─────────────────────────────────
    # Maximum unique sources fetched per research run
    RESEARCH_MAX_SOURCES: int = 5
    # HTTP fetch timeout in seconds
    RESEARCH_FETCH_TIMEOUT: int = 10
    # Maximum plain-text characters stored per source page
    RESEARCH_CONTENT_LIMIT: int = 8000
    # Seconds to wait between DuckDuckGo search requests (rate-limit safety)
    RESEARCH_REQUEST_DELAY: float = 1.5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings getter — avoids repeated IO on every request."""
    return Settings()


settings = get_settings()
