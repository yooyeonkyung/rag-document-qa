"""
RAG settings, kept separate from app/config.py so the pipeline can run
standalone (scripts/try_rag.py) without a JWT secret or AWS credentials.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_AI_DIR = Path(__file__).resolve().parents[2]


class RagSettings(BaseSettings):
    google_api_key: str | None = None

    # Model names change often - check https://ai.google.dev/gemini-api/docs/models
    embedding_model: str = "gemini-embedding-001"
    llm_model: str = "gemini-3.5-flash"
    # Total attempts per LLM call (1 = no retry; 0 would mean "SDK default").
    llm_max_retries: int = 2

    # Chunking: split within each page so every chunk maps to exactly one page.
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # How many chunks to hand the LLM per question.
    retriever_k: int = 5

    # How many past user/assistant turns to use for question rewriting and answering.
    history_max_turns: int = 3

    chroma_dir: Path = BACKEND_AI_DIR / "chroma_db"
    chroma_collection: str = "documents"

    model_config = SettingsConfigDict(
        env_file=BACKEND_AI_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )


rag_settings = RagSettings()
