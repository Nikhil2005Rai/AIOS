from pydantic_settings import BaseSettings, SettingsConfigDict


NEON_URL_HELP = (
    "DATABASE_URL is required. Create apps/api/.env with your Neon URL, for example: "
    "DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI OS API"
    environment: str = "local"
    database_url: str = ""
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expiry_minutes: int = 60
    llm_provider: str = "gemini"
    llm_model: str = "gemini-3.5-flash"
    llm_api_key: str = ""
    llm_max_output_tokens: int = 2048
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""
    llm_cache_ttl_seconds: int = 3600
    conversation_cache_ttl_seconds: int = 300
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    frontend_origin: str = "http://localhost:3000"
    encryption_key: str = ""


settings = Settings()


def validate_runtime_settings() -> None:
    if not settings.database_url:
        raise RuntimeError(NEON_URL_HELP)

    if "USER:PASSWORD@HOST" in settings.database_url:
        raise RuntimeError(NEON_URL_HELP)

    if not settings.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("DATABASE_URL must be a PostgreSQL connection string.")


def sqlalchemy_database_url() -> str:
    validate_runtime_settings()
    if settings.database_url.startswith("postgresql://"):
        return settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return settings.database_url
