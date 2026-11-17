# backend-ai

Python service for the AI side of rag-document-qa: a FastAPI app that sits
behind Spring Boot (Java) and runs the RAG pipeline (LangChain + Chroma +
Google Gemini) that answers questions about an uploaded PDF.

Spring handles users, auth, file upload (S3) and MySQL. It can't call
LangChain directly, so it talks to this service over HTTP. Users never call
this service directly.

Design history and reasoning live in `phases/` - read them before changing
anything, and update the relevant phase file along with the code.

| Phase | Topic |
|---|---|
| [01](phases/01-investigation.md) | What Spring actually outputs |
| [02](phases/02-scope-and-design.md) | FastAPI bridge scope, auth, S3 download |
| [03](phases/03-open-questions.md) | Unresolved items needing decisions outside this folder |
| [04](phases/04-rag-pipeline.md) | RAG pipeline: decisions (embedding, chunking, LLM), current status, next steps |

## Status

- Done: JWT verification (Spring's token), S3 download + per-page text
  extraction, RAG pipeline (chunk -> embed -> Chroma -> Gemini answer with
  page citations), `/api/ai/chat`, local test script.
- Not yet: ingest endpoint doesn't index into Chroma yet; Spring doesn't
  call this service yet (S3/Spring wiring is the last step - Phase 4).

## Structure

```
app/
  main.py          FastAPI app + endpoints
  config.py        JWT/AWS/CORS settings + JWT verification dependency
  schemas.py       request/response models
  rag/
    config.py      RAG settings (models, chunk size, k, Chroma path)
    ingestion.py   PDF -> per-page Documents -> chunks (never cross pages)
    vector_store.py Chroma + Gemini embeddings, index/delete/search by document_id
    prompts.py     QA prompt
    qa.py          retrieve -> prompt -> Gemini -> {answer, sources}
scripts/
  try_rag.py       run the pipeline on a local PDF, no Spring/S3/JWT
phases/            step-by-step design notes
```

## Setup

Python 3.10+.

```bash
cd backend-ai
pip install -r requirements.txt
cp .env.example .env   # set GOOGLE_API_KEY (https://aistudio.google.com/apikey)
                       # JWT_SECRET only needed for the HTTP API; AWS keys only for ingest
```

## Try the pipeline on a local PDF

```bash
# index pages 1-30 as document 1, then ask questions interactively
python -m scripts.try_rag ../file/s3-userguide.pdf --pages 1-30 --document-id 1

# ask again later without re-indexing
python -m scripts.try_rag --document-id 1 --skip-index -q "버킷을 만드는 방법은?"
```

The vector DB is persisted in `backend-ai/chroma_db/` (git-ignored). Delete
the folder to start over.

## API

Run: `uvicorn app.main:app --reload`. Every endpoint except `/health`
needs `Authorization: Bearer <jwt>` (the token Spring issued at login).

`POST /api/ai/documents/ingest` - download the PDF from S3, return per-page text
```json
// request
{ "document_id": 42, "file_url": "https://bucket.s3.region.amazonaws.com/uuid_file.pdf", "file_name": "file.pdf" }
// response
{ "document_id": 42, "file_name": "file.pdf",
  "pages": [ { "page_number": 1, "text": "..." }, { "page_number": 2, "text": "..." } ] }
```

`POST /api/ai/chat` - answer a question from one indexed document
(provisional contract with Spring, may change)
```json
// request
{ "document_id": 42, "question": "EC2 인스턴스 중지 방법?" }
// response
{ "answer": "... (p.120)", "sources": [ { "page": 120 } ] }
```
404 if the document has no indexed chunks.
