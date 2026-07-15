# Phase 2 — Narrowing the scope, and why the code looks the way it does

## The scope started too big

The first pass at this folder built a full RAG pipeline inside
`backend-ai`: JWT auth, an S3 downloader, PDF chunking
(`RecursiveCharacterTextSplitter`), Gemini embeddings, a persistent Chroma
vector store, and a `/qa/ask` endpoint that called the Gemini chat model.
That was a reasonable guess at "build the AI backend", but it collapsed two
separate jobs into one service:

1. Translating Spring's (Java) output into something Python/LangChain can
   use.
2. The actual RAG pipeline — chunking, embeddings, vector storage, and
   question answering.

The project owner corrected this mid-build: `ai/ai_core` already exists as
a separate module specifically for LangChain logic (`ingestion.py`,
`vector_store.py`, `qa.py`, `prompts.py`), and `backend-ai` was only ever
meant to be the thin bridge in front of it — receive Spring's output, fetch
the file, hand back plain text. Nothing about chunking, embeddings, vector
stores, or LLM calls belongs here. That's the current, final scope.

## Why the pieces that remain look like they do

**One file per concern, four files total** (`main.py`, `config.py`,
`schemas.py`, plus this `phases/` folder) — explicitly requested: fewer
files, no speculative structure (no `api/`, `core/`, `services/`
subpackages for a service this small). The original scaffold under
`backend-ai/app/{api,core,schemas,services}` was empty placeholder
directories the project owner hadn't started on yet, not a required
layout — they said as much and asked for concise code over matching that
shape.

**JWT is verified, not re-issued.** FastAPI has no user table and no
login endpoint. Spring is the single source of truth for auth, so this
service just decodes the same token with the same secret
(`Keys.hmacShaKeyFor(Base64.decode(secret))`, HS256, `sub` = email) and
trusts it. Duplicating a login system here would be pure risk for no
benefit — every request into this service is assumed to already carry a
Spring-issued token.

**The file is fetched via boto3 (S3 API), not a plain HTTP GET on the
url.** The bucket isn't known to be public, and going through the S3 API
with our own read-only credentials works the same way regardless of the
bucket's ACL, so this doesn't quietly break the day someone locks the
bucket down.

**Text is extracted with `pypdf` directly, not LangChain's
`PyPDFLoader`.** Since chunking/embedding is explicitly out of scope here,
pulling in `langchain-community` just to get `PyPDFLoader` (which itself
wraps `pypdf`) would add a dependency this service doesn't otherwise need.
Calling `pypdf` directly keeps `backend-ai`'s dependency list to
"FastAPI + auth + AWS + PDF text extraction" and nothing LangChain-shaped.

**One endpoint.** `POST /api/ai/documents/ingest` takes
`{document_id, file_url, file_name}` and returns
`{document_id, file_name, text}`. `document_id` is carried through
untouched — this service doesn't use it for anything except handing it back
as a correlation key, so whatever calls this (frontend today, possibly
Spring or `ai/ai_core` later) can still tie the result back to the MySQL
row it came from.
