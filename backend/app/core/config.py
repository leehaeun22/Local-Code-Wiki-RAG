from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Local Code Wiki RAG API"
    environment: str = "development"
    database_url: str = "postgresql://repowiki:repowiki@localhost:5432/repowiki"
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    github_webhook_secret: str | None = None
    frontend_url: str | None = None
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def allowed_cors_origins(self) -> list[str]:
        origins = [origin for origin in self.cors_origins if origin]

        if self.frontend_url:
            origins.append(self.frontend_url.rstrip("/"))

        return list(dict.fromkeys(origins))


settings = Settings()
