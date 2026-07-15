"""
FastAPI bridge between the Spring Boot (Java) backend and the LangChain
(Python) side. Run with: uvicorn app.main:app --reload

Spring can't call LangChain directly since it's Java, so this service takes
Spring's upload output (document id + S3 url), pulls the file down, and
hands back plain text - a form any Python/LangChain code can consume
without needing to know anything about S3 or Java.
"""
import io
from urllib.parse import unquote, urlparse

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

from app.config import get_current_user_email, settings
from app.schemas import IngestRequest, IngestResponse

app = FastAPI(title="RAG AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Fetch the file Spring uploaded and hand back its plain text.

    Chunking, embedding, vector storage and QA all live in ai/ai_core, not
    here - this endpoint's only job is Java-output -> Python-usable text.
    """
    try:
        pdf_bytes = _download_from_s3(request.file_url)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    pages = PdfReader(io.BytesIO(pdf_bytes)).pages
    text = "\n".join(page.extract_text() or "" for page in pages)
    if not text.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No extractable text found in the document")

    return IngestResponse(document_id=request.document_id, file_name=request.file_name, text=text)
