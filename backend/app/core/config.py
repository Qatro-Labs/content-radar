from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    database_url: str = "postgresql+asyncpg://radar:radar@localhost:5433/radar"

    youtube_api_key: str = ""
    brave_api_key: str = ""

    llm_api_key: str = ""
    llm_model: str = ""

    # Separados por coma en el .env
    cors_allowed_origins: str = "http://localhost:5173"
    mcp_public_url: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
