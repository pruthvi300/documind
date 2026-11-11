"""DocuMind configuration, loaded from environment variables and `.env`."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "DocuMind"
    APP_VERSION: str = "1.1.0"
    DEBUG: bool = False
    SQL_ECHO: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # LLM provider: "openai" or "ollama"
    LLM_PROVIDER: str = "ollama"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MAX_TOKENS: int = 1024

    # Embeddings: "openai" or "ollama"
    EMBEDDING_PROVIDER: str = "ollama"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # RAG
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 5
    # Chunks scoring below this cosine relevance (0-1) are ignored. 0 disables the filter.
    MIN_RELEVANCE_SCORE: float = 0.3
    HISTORY_MESSAGES: int = 6

    # Storage
    DATABASE_URL: str = "postgresql+asyncpg://documind:documind123@localhost:5432/documind"
    # Empty REDIS_URL disables the embedding cache.
    REDIS_URL: str = "redis://localhost:6379/0"
    EMBEDDING_CACHE_TTL_SECONDS: int = 60 * 60 * 24 * 30
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = ["pdf", "txt", "md", "csv", "docx"]

    @property
    def active_model(self) -> str:
        return self.OPENAI_MODEL if self.LLM_PROVIDER == "openai" else self.OLLAMA_MODEL

    @property
    def active_embedding_model(self) -> str:
        return self.OPENAI_EMBEDDING_MODEL if self.EMBEDDING_PROVIDER == "openai" else self.OLLAMA_EMBEDDING_MODEL


@lru_cache
def get_settings() -> Settings:
    return Settings()
