from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "interp-eval"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://eval:eval@db:5432/eval"

    # LLM providers (filled in later milestones)
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # Local model path for probing (filled in M6)
    local_model_name: str = "Qwen/Qwen2.5-3B-Instruct"


settings = Settings()
