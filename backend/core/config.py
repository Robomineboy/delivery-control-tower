"""
core/config.py

Centralized configuration via pydantic-settings.
All thresholds are externalized here — a client can tune them
without touching agent logic.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    groq_api_key: str = ""
    openai_api_key: str = ""
    primary_llm_provider: str = "groq"
    groq_model: str = "llama3-70b-8192"
    openai_model: str = "gpt-4o"

    # Confidence thresholds — gates downstream agent behavior
    min_retrieval_confidence: float = 0.65
    min_planning_confidence: float = 0.70
    min_critic_confidence: float = 0.75

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    environment: str = "development"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Audit
    audit_db_path: str = "data/audit.db"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
