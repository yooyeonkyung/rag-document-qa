# Phase 3 — Open questions / not yet resolved

Things noticed while building this that need a decision or a change
outside `backend-ai` before the pipeline works end-to-end. None of these
were fixed here — `backend/` was explicitly off-limits for this task.

## 1. Spring's response doesn't carry `file_url` yet

`POST /api/documents` currently returns a bare document id. This
service's `/api/ai/documents/ingest` needs `file_url` in its request body
(see Phase 1). Something has to close that gap — most likely one of:

- Extend Spring's response DTO to include `s3Url` (and `fileName`)
  alongside the id, so the frontend can pass it straight through.
- A new `GET /api/documents/{id}` endpoint the frontend calls first.

Either is a small Spring change, but it's the teammate's code and wasn't
touched here. Until it happens, `/api/ai/documents/ingest` can be
exercised manually (e.g. with a hand-built request body) but not end-to-end
from the real upload flow.

## 2. Scanned / image-only PDFs produce no text

`pypdf`'s `extract_text()` only reads embedded text — it does not OCR
images. A scanned PDF with no text layer will trigger the
`422 "No extractable text found"` response. If scanned documents are
expected, an OCR step (e.g. `pytesseract`) would need to go in front of or
instead of this extraction — not added here since it wasn't asked for and
adds a system dependency (Tesseract).

## 3. `jwt.secret` is committed in plaintext

`backend/src/main/resources/application.yml` has the JWT signing secret
checked into git. This service depends on that exact value matching
`JWT_SECRET` in its own `.env` (not committed), so it was necessary to read
it, but the secret being in source control at all is worth the team
rotating out via an environment variable at some point — flagged here, not
changed.

## 4. What `ai/ai_core` still needs to do

This service's only output is `{document_id, file_name, text}`. Everything
after that — chunking, embeddings, the Chroma vector store, and answering
questions with an LLM — is unbuilt (`ai/ai_core/*.py` are all currently
empty files). The project owner has chosen **Google Gemini**
(`langchain-google-genai`, already installed) as the LLM/embedding
provider for that next phase, over the OpenAI mentioned in the root
`README.md`.
