import os

from pydantic_settings import BaseSettings

env = os.environ.get("NYRA_ENV", "development")
env_file = f".env.{env}" if env != "development" else ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "NYRA Backend"
    DATABASE_URL: str = "postgresql://nyra_user:nyra_password@localhost:5432/nyra_db"
    GEMINI_API_KEY: str = ""
    JWT_SECRET: str

    @property
    def jwt_secret_key(self) -> str:
        if self.JWT_SECRET == "supersecretjwtkey_replace_me_in_production":
            raise ValueError(
                "CRITICAL SECURITY RISK: JWT_SECRET is using the default insecure value."
            )
        return self.JWT_SECRET

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GROQ_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    class Config:
        env_file = env_file
        extra = "ignore"


settings = Settings()

# Startup validation — loud warnings for missing critical keys
import logging as _log

_startup_logger = _log.getLogger("nyra.startup")
if not settings.GEMINI_API_KEY:
    _startup_logger.critical(
        "⚠️  GEMINI_API_KEY is not set! All LLM calls will fail. "
        "Set it in backend/.env or as an environment variable."
    )
if not settings.GROQ_API_KEY:
    _startup_logger.info("GROQ_API_KEY not set — Groq fallback is disabled.")
if not settings.OPENROUTER_API_KEY:
    _startup_logger.info("OPENROUTER_API_KEY not set — OpenRouter fallback is disabled.")
