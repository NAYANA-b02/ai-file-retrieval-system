from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
ROOT_ENV_FILE = BASE_DIR.parent / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "AI-Based Intelligent File Retrieval System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_file_retrieval_db"

    FRONTEND_ORIGIN: str = "http://localhost:5173"

    UPLOAD_DIR: str = "app/data/uploads"
    FAISS_INDEX_DIR: str = "app/data/indexes"
    MAX_UPLOAD_SIZE_MB: int = 10

    SESSION_COOKIE_NAME: str = "ai_file_retrieval_session"
    SESSION_EXPIRE_HOURS: int = 24
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    KEYWORD_SEARCH_WEIGHT: float = 0.4
    SEMANTIC_SEARCH_WEIGHT: float = 0.6

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    RAG_SIMILARITY_THRESHOLD: float = 0.35

    model_config = SettingsConfigDict(
        env_file=(str(ENV_FILE), str(ROOT_ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
