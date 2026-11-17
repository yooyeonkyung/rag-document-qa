"""
Chroma (persisted to disk) + Gemini embeddings. All documents share one
collection; queries are scoped by the `document_id` metadata filter.
"""
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.rag.config import rag_settings


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


def delete_document(document_id: int) -> None:
    store = get_vector_store()
    ids = store.get(where={"document_id": document_id}, include=[])["ids"]
    if ids:
        store.delete(ids=ids)


def index_document(document_id: int, chunks: list[Document]) -> int:
    """(Re)index a document: drop its old chunks first so re-ingesting never duplicates."""
    delete_document(document_id)
    ids = [f"{document_id}-p{c.metadata['page']}-{c.metadata['chunk_index']}" for c in chunks]
    get_vector_store().add_documents(chunks, ids=ids)
    return len(chunks)


def search(document_id: int, query: str, k: int) -> list[Document]:
    return get_vector_store().similarity_search(query, k=k, filter={"document_id": document_id})
