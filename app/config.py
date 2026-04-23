from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "legalens"
    debug: bool = False
    model_name: str = "all-MiniLM-L6-v2"
    similarity_threshold: float = 0.85
    max_document_bytes: int = 5 * 1024 * 1024  # 5 MB


settings = Settings()
