# backend-ai

A thin FastAPI bridge between the Spring Boot backend (Java) and the
LangChain/RAG pipeline (Python, in `ai/ai_core`).

Spring Boot handles auth, file upload, and S3/MySQL storage. It can't call
LangChain directly since it's Java. This service receives Spring's upload
output (a document id + S3 url), downloads the file, extracts its text, and
hands back plain text - a form any Python code can consume without knowing
about S3, Java, or JWTs. It does not chunk, embed, store vectors, or answer
questions; that's `ai/ai_core`'s job.

See `phases/` for the reasoning behind each design decision.

## Setup

```bash
cd backend-ai
pip install -r requirements.txt
cp .env.example .env   # fill in JWT_SECRET (copy from backend's application.yml) and AWS creds
uvicorn app.main:app --reload
```

## Endpoint

`POST /api/ai/documents/ingest`
Headers: `Authorization: Bearer <jwt>` (same token Spring issued at login)
Body:
```json
{ "document_id": 42, "file_url": "https://bucket.s3.region.amazonaws.com/uuid_file.pdf", "file_name": "file.pdf" }
```
Response:
```json
{ "document_id": 42, "file_name": "file.pdf", "text": "...extracted text..." }
```
