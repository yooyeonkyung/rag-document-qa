"""
Question -> retrieve chunks of one document -> Gemini answer + cited pages.
"""
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.rag.config import rag_settings
from app.rag.prompts import QA_PROMPT
from app.rag.vector_store import search


class DocumentNotIndexedError(LookupError):
    pass


@lru_cache
def get_llm() -> BaseChatModel:
    return ChatGoogleGenerativeAI(model=rag_settings.llm_model, google_api_key=rag_settings.google_api_key)


def _format_context(chunks: list[Document]) -> str:
    return "\n\n---\n\n".join(f"[p.{c.metadata['page']}]\n{c.page_content}" for c in chunks)


def answer_question(document_id: int, question: str) -> dict:
    chunks = search(document_id, question, k=rag_settings.retriever_k)
    if not chunks:
        raise DocumentNotIndexedError(f"Document {document_id} has not been indexed")

    messages = QA_PROMPT.invoke({"context": _format_context(chunks), "question": question})
    answer = get_llm().invoke(messages).text
    pages = sorted({c.metadata["page"] for c in chunks})
    return {"answer": answer, "sources": [{"page": p} for p in pages]}
