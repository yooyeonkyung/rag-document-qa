"""
Chroma (persisted to disk) + Gemini embeddings. All documents share one
collection; queries are scoped by the `document_id` metadata filter.
"""
import logging
import time
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.rag.config import rag_settings
from app.rag.errors import is_temporary_model_error

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 90  # stay under the free tier's 100 requests/minute
RATE_LIMIT_WAIT_SECONDS = 60
MAX_RETRIES = 3


def get_embeddings() -> Embeddings:
    return GoogleGenerativeAIEmbeddings(
        model=rag_settings.embedding_model, google_api_key=rag_settings.google_api_key
    )


@lru_cache
def get_vector_store() -> Chroma:
    return Chroma(
        collection_name=rag_settings.chroma_collection,
        embedding_function=get_embeddings(),
        persist_directory=str(rag_settings.chroma_dir),
    )


def delete_document(document_id: int) -> int:
    """Delete all chunks of a document; returns how many were deleted (0 if none)."""
    store = get_vector_store()
    ids = store.get(where={"document_id": document_id}, include=[])["ids"]
    if ids:
        store.delete(ids=ids)
    return len(ids)


def _add_with_retry(store: Chroma, chunks: list[Document], ids: list[str]) -> None:
    for attempt in range(MAX_RETRIES + 1):
        try:
            store.add_documents(chunks, ids=ids)
            return
        except Exception as exc:
            if not is_temporary_model_error(exc) or attempt == MAX_RETRIES:
                raise
            logger.warning("Embedding rate-limited/unavailable, retrying in %ss", RATE_LIMIT_WAIT_SECONDS)
            time.sleep(RATE_LIMIT_WAIT_SECONDS)


def index_document(document_id: int, chunks: list[Document]) -> int:
    """(Re)index a document: drop its old chunks first so re-ingesting never duplicates."""
    delete_document(document_id)
    return add_chunks(document_id, chunks)


def add_chunks(document_id: int, chunks: list[Document]) -> int:
    """Embed and store chunks without deleting anything (used per segment by jobs.py).

    Chunks are embedded in batches because the Gemini free tier allows only
    100 embedding requests (= chunks) per minute; on a 429/503 we wait and retry.
    Ids are deterministic and Chroma upserts, so re-adding a chunk overwrites it.
    """
    store = get_vector_store()
    ids = [f"{document_id}-p{c.metadata['page']}-{c.metadata['chunk_index']}" for c in chunks]
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        end = start + EMBED_BATCH_SIZE
        _add_with_retry(store, chunks[start:end], ids[start:end])
        logger.info("Indexed %d/%d chunks", min(end, len(chunks)), len(chunks))
    return len(chunks)


def search(document_id: int, query: str, k: int) -> list[Document]:
    return get_vector_store().similarity_search(query, k=k, filter={"document_id": document_id})
