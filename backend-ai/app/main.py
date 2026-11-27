"""
FastAPI bridge between the Spring Boot (Java) backend and the RAG pipeline
in app/rag (LangChain + Chroma + Gemini). Run with: uvicorn app.main:app --reload

- POST /api/ai/documents/ingest: S3 PDF -> per-page text
- POST /api/ai/chat: question about an indexed document -> answer + cited pages
- POST /api/ai/documents/{document_id}/index: start/resume background indexing
- GET /api/ai/documents/{document_id}/status: indexing progress
- DELETE /api/ai/documents/{document_id}: remove a document's chunks from Chroma

Gemini overload/rate-limit errors become 503 "try again shortly" responses.
"""
import logging
from contextlib import asynccontextmanager
from urllib.parse import unquote, urlparse

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_current_user_email, settings
from app.rag.errors import DocumentNotIndexedError, ModelUnavailableError
from app.rag import jobs
from app.rag.ingestion import load_pdf_pages
from app.rag.qa import answer_question
from app.rag.vector_store import delete_document
from app.schemas import (
    ChatRequest,
    ChatResponse,
    DeleteDocumentResponse,
    IndexRequest,
    IndexStatusResponse,
    IngestRequest,
    IngestResponse,
    PageText,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Background jobs die with the process; mark them resumable.
    jobs.mark_interrupted_jobs()
    yield


app = FastAPI(title="RAG AI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ModelUnavailableError)
def model_unavailable_handler(_request: Request, exc: ModelUnavailableError) -> JSONResponse:
    """Gemini overloaded (503) or rate-limited (429): tell the caller to retry later."""
    logger.warning("Gemini temporarily unavailable: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The AI model is temporarily unavailable. Please try again in a moment."},
    )


def _parse_s3_url(url: str) -> tuple[str, str]:
    """Split an S3 object URL into (bucket, key).

    Spring's S3UploadService builds virtual-hosted-style URLs
    (https://<bucket>.s3.<region>.amazonaws.com/<key>) via the AWS SDK v2.
    Path-style (https://s3.<region>.amazonaws.com/<bucket>/<key>) is also
    accepted, in case that ever changes.
    """
    parsed = urlparse(url)
    path = unquote(parsed.path).lstrip("/")
    if parsed.netloc.startswith("s3."):
        bucket, _, key = path.partition("/")
    else:
        bucket, key = parsed.netloc.split(".")[0], path
    if not bucket or not key:
        raise ValueError(f"Could not parse an S3 bucket/key out of URL: {url}")
    return bucket, key


def _download_from_s3(file_url: str) -> bytes:
    bucket, key = _parse_s3_url(file_url)
    client = boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )
    try:
        return client.get_object(Bucket=bucket, Key=key)["Body"].read()
    except (ClientError, NoCredentialsError) as exc:
        raise FileNotFoundError(f"Failed to download '{file_url}' from S3: {exc}") from exc


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/ai/documents/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest, _owner_email: str = Depends(get_current_user_email)) -> IngestResponse:
    """Fetch the file Spring uploaded and hand back its text, page by page.

    Not yet wired into indexing (app/rag) - S3/Spring integration is the
    last step, see phases/04-rag-pipeline.md.
    """
    try:
        pdf_bytes = _download_from_s3(request.file_url)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    pages = [PageText(page_number=p.metadata["page"], text=p.page_content) for p in load_pdf_pages(pdf_bytes)]
    if not pages:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No extractable text found in the document")

    return IngestResponse(document_id=request.document_id, file_name=request.file_name, pages=pages)


@app.post("/api/ai/chat", response_model=ChatResponse)
def chat(request: ChatRequest, _owner_email: str = Depends(get_current_user_email)) -> ChatResponse:
    """Answer a question using only the given document's indexed chunks.

    With history, the question is first rewritten into a standalone one so
    follow-ups like "그거 삭제는?" retrieve the right chunks.
    """
    history = [turn.model_dump() for turn in request.history]
    try:
        return ChatResponse(**answer_question(request.document_id, request.question, history))
    except DocumentNotIndexedError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _status_response(job: dict) -> IndexStatusResponse:
    return IndexStatusResponse(
        document_id=job["document_id"],
        status=job["status"],
        total_pages=job["total_pages"],
        indexed_pages=job["last_indexed_page"],
        searchable=job["last_indexed_page"] > 0,
        running=job["running"],
        error=job["error"],
        updated_at=job["updated_at"],
    )


@app.post(
    "/api/ai/documents/{document_id}/index",
    response_model=IndexStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def index(
    document_id: int,
    request: IndexRequest,
    background_tasks: BackgroundTasks,
    _owner_email: str = Depends(get_current_user_email),
) -> IndexStatusResponse:
    """Start (or resume) indexing in the background and return immediately (202).

    Poll GET .../status for progress. 409 if this document is already being indexed.
    """
    try:
        job = jobs.start_job(document_id, request.file_name, resume=request.resume)
    except jobs.JobAlreadyRunningError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    background_tasks.add_task(jobs.run_job, document_id, lambda: _download_from_s3(request.file_url))
    return _status_response(job)


@app.get("/api/ai/documents/{document_id}/status", response_model=IndexStatusResponse)
def index_status(document_id: int, _owner_email: str = Depends(get_current_user_email)) -> IndexStatusResponse:
    job = jobs.get_job(document_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No indexing job for document {document_id}")
    return _status_response(job)


@app.delete("/api/ai/documents/{document_id}", response_model=DeleteDocumentResponse)
def delete(document_id: int, _owner_email: str = Depends(get_current_user_email)) -> DeleteDocumentResponse:
    """Remove a document's chunks and indexing job (call when Spring deletes the document).

    Idempotent: deleting a document that was never indexed returns deleted_chunks=0.
    409 while it is being indexed (the job would keep adding chunks).
    """
    if jobs.is_running(document_id):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Document {document_id} is being indexed; try again later")
    deleted = delete_document(document_id)
    jobs.delete_job(document_id)
    return DeleteDocumentResponse(document_id=document_id, deleted_chunks=deleted)
