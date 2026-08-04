from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Point to repo-root .env regardless of where Python is launched from
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        extra="ignore",
    )

    app_name: str = "llm-eval-with-probes"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://eval:eval@db:5432/eval"

    groq_api_key: str = ""
    gemini_api_key: str = ""

    # Comma-separated origins allowed on top of the built-in localhost/Vercel
    # patterns — used to whitelist a deployed dashboard's own domain.
    cors_allow_origins: str = ""

    default_subject_model: str = "llama-3.1-8b-instant"
    default_judge_model: str = "llama-3.3-70b-versatile"
    default_gemini_model: str = "gemini-2.0-flash"

    local_model_name: str = "Qwen/Qwen2.5-3B-Instruct"

    max_retries: int = 4
    initial_retry_delay_seconds: float = 1.0


settings = Settings()
