"""
(Follow-up question -> standalone question) -> retrieve chunks of one
document -> Gemini answer + cited pages.
"""
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.rag.config import rag_settings
from app.rag.errors import DocumentNotIndexedError, ModelUnavailableError, is_temporary_model_error
from app.rag.prompts import CONDENSE_QUESTION_PROMPT, QA_PROMPT
from app.rag.vector_store import search


@lru_cache
def get_llm() -> BaseChatModel:
    return ChatGoogleGenerativeAI(
        model=rag_settings.llm_model,
        google_api_key=rag_settings.google_api_key,
        # The SDK default (6) retries 503s/429s so many times that one request can
        # burn the free tier's daily quota; fail fast and let the client retry.
        max_retries=rag_settings.llm_max_retries,
    )


def _format_context(chunks: list[Document]) -> str:
    return "\n\n---\n\n".join(f"[p.{c.metadata['page']}]\n{c.page_content}" for c in chunks)


def _to_messages(history: list[dict]) -> list[BaseMessage]:
    """[{role: user|assistant, content}] -> LangChain messages, last N turns only."""
    recent = history[-rag_settings.history_max_turns * 2 :] if rag_settings.history_max_turns else []
    return [HumanMessage(h["content"]) if h["role"] == "user" else AIMessage(h["content"]) for h in recent]


def condense_question(question: str, history: list[BaseMessage]) -> str:
    if not history:
        return question
    messages = CONDENSE_QUESTION_PROMPT.invoke({"history": history, "question": question})
    return get_llm().invoke(messages).text.strip() or question


def answer_question(document_id: int, question: str, history: list[dict] | None = None) -> dict:
    """Raises DocumentNotIndexedError, or ModelUnavailableError when Gemini is overloaded/rate-limited."""
    try:
        return _answer_question(document_id, question, history)
    except Exception as exc:
        if is_temporary_model_error(exc):
            raise ModelUnavailableError(str(exc)) from exc
        raise


def _answer_question(document_id: int, question: str, history: list[dict] | None) -> dict:
    history_messages = _to_messages(history or [])
    search_query = condense_question(question, history_messages)

    chunks = search(document_id, search_query, k=rag_settings.retriever_k)
    if not chunks:
        raise DocumentNotIndexedError(f"Document {document_id} has not been indexed")

    messages = QA_PROMPT.invoke(
        {"context": _format_context(chunks), "history": history_messages, "question": question}
    )
    answer = get_llm().invoke(messages).text
    pages = sorted({c.metadata["page"] for c in chunks})
    return {"answer": answer, "search_query": search_query, "sources": [{"page": p} for p in pages]}
