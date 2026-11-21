"""
Errors the RAG pipeline raises for the API layer to turn into HTTP responses.
"""
from langchain_google_genai._common import GoogleGenerativeAIError
from langchain_google_genai.chat_models import GoogleAPIError, GoogleRateLimitError

_TEMPORARY_MARKERS = ("RESOURCE_EXHAUSTED", "UNAVAILABLE", "429", "503")


class DocumentNotIndexedError(LookupError):
    pass


class ModelUnavailableError(RuntimeError):
    """Gemini is overloaded (5xx) or rate-limited (429) - worth retrying later."""


def is_temporary_model_error(exc: Exception) -> bool:
    # Chat model errors are already classified by langchain-google-genai.
    if isinstance(exc, (GoogleRateLimitError, GoogleAPIError)):
        return True
    # Embedding errors all come as GoogleGenerativeAIError; the status is only in the message.
    return isinstance(exc, GoogleGenerativeAIError) and any(m in str(exc) for m in _TEMPORARY_MARKERS)
