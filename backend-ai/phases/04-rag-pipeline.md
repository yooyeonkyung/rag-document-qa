# Phase 4 — Building the RAG pipeline

## Where the code lives

`app/rag/` inside `backend-ai`, not the separate `ai/ai_core` folder.
FastAPI has to import the pipeline, and Python can't import from a sibling
folder without installing it as a package (`pip install -e ../ai`) or path
hacks. One person owns both, so one folder is simpler. `ai/` is now unused.

## Order of work

1. **Pipeline standalone on local PDFs** (done) - `scripts/try_rag.py`
   indexes `file/*.pdf` and answers questions with no Spring, S3 or JWT, so
   chunking/embedding/prompt changes can be iterated quickly.
2. **FastAPI endpoints** (in progress) - `/api/ai/chat` done; ingest still
   only returns text and doesn't index yet.
3. **Quality pass** (todo) - small eval set (~10 questions with known
   answer pages) to compare settings, incl. Gemini embeddings vs BGE-M3.
4. **S3/Spring integration** (last) - ingest indexes into Chroma; Spring
   calls ingest after upload and `/api/ai/chat` for questions, and stores
   chat history in MySQL. Agreed with the Spring teammate at that point.

## Decisions (chosen by the project owner from presented options)

| Item | Choice | Alternatives considered | Why |
|---|---|---|---|
| Embedding | Gemini (`gemini-embedding-001`) | BGE-M3 local; both at once | Same API key as the LLM, light install, fastest to get running. BGE-M3 comparison comes in step 3. |
| Chunking | Split each page separately (`RecursiveCharacterTextSplitter`) | Whole-document split; semantic chunking | A chunk never spans two pages, so cited page numbers are always exact. |
| Chunk size / overlap | 1000 / 150 characters | 500/100, 1500/200 | Common default; roughly one paragraph/procedure of a manual. |
| LLM | Gemini Flash (`gemini-3.5-flash`) | Gemini Pro | Fast, cheap, generous free tier; enough for grounded QA. |
| Retriever k | 5 chunks per question | 4 (initial placeholder) | Project owner's choice: a bit more context per answer at a small token cost. |
| Chat history | Rewrite the follow-up into a standalone question with the LLM, retrieve with that, and answer with the history in the prompt | (A) question only, no history; (B) history only in the answer prompt | (A) can't handle "그거 삭제는?"; (B) still *searches* with the vague follow-up and retrieves the wrong chunks. Costs one extra LLM call when there's history. |

All of these are overridable in `.env` (see `app/rag/config.py`); model
names change often, so check https://ai.google.dev/gemini-api/docs/models.

## Placeholder values not yet decided

Set just so the pipeline runs; to be decided with the project owner:

- QA prompt (`app/rag/prompts.py`) - answer only from excerpts, say so if
  not found, answer in the question's language, cite `(p.N)`. Suggested
  addition (not applied): "lead with a short answer, then steps if needed".
- `history_max_turns = 3` - how many past user/assistant turns are used.

## How it works

- `ingestion.py`: `load_pdf_pages` -> one `Document` per page (1-based
  `page`, empty pages skipped). `split_pages` -> chunks with metadata
  `document_id`, `page`, `chunk_index`, `file_name`.
- `vector_store.py`: one persisted Chroma collection (`backend-ai/chroma_db/`)
  for all documents; every search is filtered by `document_id`.
  `index_document` deletes a document's old chunks first, so re-indexing
  never duplicates. Chunk ids are `{document_id}-p{page}-{chunk_index}`.
  Embedding is done in batches of 90 chunks: the Gemini free tier allows
  only 100 embedding requests (= chunks) per minute, and a 116-chunk
  document failed with 429 RESOURCE_EXHAUSTED before this. On a 429 it
  waits 60s and retries (max 3).
- `qa.py`: if there's history, `CONDENSE_QUESTION_PROMPT` rewrites the
  follow-up into a standalone `search_query` -> top-k search in that
  document -> `QA_PROMPT` with `[p.N]`-labelled excerpts + recent history ->
  Gemini -> `{answer, search_query, sources: [{page}]}` (sources = pages of
  the retrieved chunks). No chunks -> `DocumentNotIndexedError` -> HTTP 404.
- Chat history is NOT stored here. Spring owns it (MySQL `chat_messages`)
  and sends it in each `/api/ai/chat` request.

## Verified

With fake embeddings/LLM (no API key yet): 10 pages of the S3 guide ->
52 chunks (max 999 chars), re-index keeps 52, searches stay within the
requested document, `/api/ai/chat` returns 200 / 404 (unindexed) / 401 (no
token).

With real Gemini: pages 1-15 of the S3 guide (85 chunks) -> answered that
the excerpts only contain the table of contents (correct: those pages are
the TOC). Pages 26-70 (116 chunks) indexed fine after adding batching, but
answering hit `503 UNAVAILABLE` (model overloaded) three times in a row.
The chat-history rewrite is verified with fake models only (rewrite runs only
when there's history, retrieval uses the rewritten question, API 200 / 404 /
401 / 422); the real-Gemini follow-up test hit the **free-tier daily limit of
20 generate requests for the Flash model** - the SDK's automatic retries on
503 used it up quickly. Re-test after the daily reset.

## Note on the sample PDFs

`file/ec2-ug.pdf` is ~3,800 pages and `file/s3-userguide.pdf` ~3,500.
Embedding a whole guide takes a long time and can hit the free-tier rate
limit, so test with `--pages 1-30` or similar.

## Next steps (agreed 2026-11-17)

1. Gemini 503/429 during answering -> return a "temporarily unavailable,
   try again shortly" error (HTTP 503) instead of a 500.
2. `DELETE /api/ai/documents/{document_id}` -> remove the document's
   chunks from Chroma.
3. Large documents (3,000+ pages): free tier works but is slow (~100
   chunks/minute plus a daily cap). Options to decide: page limit,
   background indexing with progress, local BGE-M3 embeddings (no rate
   limit), or a paid tier.
4. Evaluation: golden Q&A set with known answer pages -> retrieval metrics
   (hit rate / Recall@k, MRR) and answer metrics (faithfulness, relevance,
   LLM-as-judge or RAGAS); use it to compare k, chunk size, Gemini vs BGE-M3.
5. Monitoring: log every request (question, search_query, retrieved chunk
   scores, answer, latency, errors) and track drift - data drift (question
   embedding/topic distribution), prediction drift (answer length,
   "not found" rate, retrieval scores), concept drift (eval-set accuracy /
   user feedback over time).
6. Last: React UI and S3/Spring integration.
