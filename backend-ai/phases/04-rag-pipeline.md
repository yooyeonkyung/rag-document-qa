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

All of these are overridable in `.env` (see `app/rag/config.py`); model
names change often, so check https://ai.google.dev/gemini-api/docs/models.

## Placeholder values not yet decided

Set just so the pipeline runs; to be decided with the project owner:

- `retriever_k = 4` - how many chunks go to the LLM per question.
- QA prompt (`app/rag/prompts.py`) - answer only from excerpts, say so if
  not found, answer in the question's language, cite `(p.N)`.
- No chat history is sent to the LLM (each question stands alone).

## How it works

- `ingestion.py`: `load_pdf_pages` -> one `Document` per page (1-based
  `page`, empty pages skipped). `split_pages` -> chunks with metadata
  `document_id`, `page`, `chunk_index`, `file_name`.
- `vector_store.py`: one persisted Chroma collection (`backend-ai/chroma_db/`)
  for all documents; every search is filtered by `document_id`.
  `index_document` deletes a document's old chunks first, so re-indexing
  never duplicates. Chunk ids are `{document_id}-p{page}-{chunk_index}`.
- `qa.py`: top-k search in that document -> prompt with `[p.N]`-labelled
  excerpts -> Gemini -> `{answer, sources: [{page}]}` (sources = pages of
  the retrieved chunks). No chunks -> `DocumentNotIndexedError` -> HTTP 404.

## Verified

With fake embeddings/LLM (no API key yet): 10 pages of the S3 guide ->
52 chunks (max 999 chars), re-index keeps 52, searches stay within the
requested document, `/api/ai/chat` returns 200 / 404 (unindexed) / 401 (no
token). Not yet run against real Gemini.

## Note on the sample PDFs

`file/ec2-ug.pdf` is ~3,800 pages and `file/s3-userguide.pdf` ~3,500.
Embedding a whole guide takes a long time and can hit the free-tier rate
limit, so test with `--pages 1-30` or similar.
