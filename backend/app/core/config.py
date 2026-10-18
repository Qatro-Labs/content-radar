from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Una variable vacía (`JEV_VERIFY_CLAIMS=` en Railway) toma el valor por defecto: sin esto,
    # un bool vacío no se puede leer y no arrancan ni la API ni los jobs.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    app_env: str = "local"
    database_url: str = "postgresql+asyncpg://radar:radar@localhost:5433/radar"

    youtube_api_key: str = ""
    brave_api_key: str = ""
    scrapecreators_api_key: str = ""
    twitterapi_api_key: str = ""

    typesafe_api_key: str = ""
    jev_model: str = "jev-1.13.0"
    # Jev verifica cada afirmación de «por qué importa». Encendido desde que `claim.v2` con umbral
    # 0,6 pasó su criterio de adopción (data/evaluations/jev_claim_adoption_eval.md).
    jev_verify_claims: bool = True

    llm_api_key: str = ""
    llm_model: str = ""

    # Separados por coma en el .env
    cors_allowed_origins: str = "http://localhost:5173"
    mcp_public_url: str = ""

    # Apagado: todo funciona sin sesión, como antes. Encendido, las rutas que gastan LLM (agente y
    # briefs) piden un access token de Supabase Auth.
    auth_required: bool = False
    # URL del proyecto (https://<ref>.supabase.co): de ella salen el JWKS y el `iss` esperado.
    supabase_url: str = ""

    # Ejecución de `analyze` revisada a mano para la demo (CLAUDE.md §13). Sin valor, la API y el
    # MCP sirven la última ejecución correcta, que cambia con cada recolección.
    demo_run_id: int | None = None

    @field_validator("demo_run_id", mode="before")
    @classmethod
    def _empty_is_unset(cls, value: object) -> object:
        # `DEMO_RUN_ID=` vacío en el .env o en Railway significa "sin fijar", no un error.
        return None if value == "" else value

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
