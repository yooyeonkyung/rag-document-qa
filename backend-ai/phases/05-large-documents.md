# Phase 5 — Large documents: background, resumable indexing

## Problem

`file/ec2-ug.pdf` is ~3,800 pages ≈ 20k chunks. The Gemini free tier embeds
100 chunks per minute, so indexing takes 3+ hours and can stop on a quota
error halfway. That can't run inside one HTTP request, and losing all
progress on an error would waste the quota already spent.

## Decision (project owner, 2026-11-23)

Options presented: (A) page limit, (B) background indexing + progress API,
(C) local embeddings (BGE-M3), (D) paid tier.

Chosen: **B combined with A as "priority pages", not a hard limit.**
- Pages 1-500 are indexed first; after that the document is already
  searchable (status `partial`).
- The rest keeps indexing in the background, 50 pages per segment, saving
  progress after each segment.
- On a Gemini quota/overload error the job is `paused`; resuming continues
  after the last finished page.
- If this is still too slow: consider the paid tier (D). The embedding
  model itself will be chosen from evaluation results (Phase 6), comparing
  several models incl. local ones (C).

## Design

`app/rag/jobs.py`, state in SQLite (`backend-ai/data/index_jobs.sqlite3`,
git-ignored; stdlib `sqlite3`, no new dependency). One row per document:
`document_id, file_name, total_pages, last_indexed_page, status, error, updated_at`.

```
queued -> indexing -> partial -> completed
             |          |
             +----------+--> paused  (Gemini 429/5xx after retries; resumable)
                        +--> failed  (anything else, e.g. S3 download error; resumable)
```

- `start_job(document_id, file_name, resume)`: fresh start deletes old
  chunks and resets progress; `resume=True` on a paused/failed job keeps
  them. Raises `JobAlreadyRunningError` if a job for that document is
  running (in-process set + lock).
- `run_job(document_id, load_pdf)`: opens the PDF once, then for each
  50-page segment: read pages -> chunk -> `add_chunks` (batched embedding
  with retry, from Phase 4) -> save `last_indexed_page`. `load_pdf` is a
  callable so the API can pass an S3 download and the script a local file.
- Chunk ids are deterministic (`{doc}-p{page}-{i}`) and Chroma upserts, so if
  a segment fails halfway and is redone on resume, nothing is duplicated.
- On startup (`lifespan` in `main.py`), jobs left `queued/indexing/partial`
  are marked `paused` ("Interrupted by server restart"), since background
  tasks die with the process.

### API

- `POST /api/ai/documents/{id}/index` `{file_url, file_name?, resume?}` ->
  **202** with the status, indexing runs via FastAPI `BackgroundTasks`.
  409 if already running.
- `GET /api/ai/documents/{id}/status` -> `{status, total_pages,
  indexed_pages, searchable, running, error, updated_at}`; 404 if no job.
- `DELETE /api/ai/documents/{id}` now also removes the job row, and returns
  409 while the document is being indexed.
- `/api/ai/documents/ingest` (returns text) is unchanged; Spring will call
  `.../index` instead when the integration happens.

### Script

`python -m scripts.try_rag <pdf> --document-id N --index-only [--resume]`
runs the same job runner in the foreground. `--pages a-b` still does a
quick one-shot index of a page range (used for experiments/evaluation).

## Limitations (fine for a local portfolio project, worth knowing)

- `BackgroundTasks` runs in the API process: a restart stops the job (it's
  marked paused and must be resumed with `resume=true`). Production would
  use a separate worker + queue (Celery/RQ/Arq) with automatic retries.
- No automatic resume after a quota pause; the caller resumes (e.g. the
  next day for a daily cap).
- One process only - the "already running" check is in memory.

## Verified

Not tested yet (waiting for approval to run tests).
