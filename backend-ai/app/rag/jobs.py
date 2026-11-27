"""
Resumable background indexing for large PDFs.

A 3,800-page PDF is ~20k chunks; at the Gemini free tier's 100 embeddings
per minute that's hours, so indexing can't happen inside one HTTP request.
Instead the document is indexed in page segments and progress is saved in
SQLite after each one:

    queued -> indexing -> partial -> completed
                 |          |
                 +----------+--> paused  (Gemini quota/overload; resume later)
                            +--> failed  (unexpected error)

- "partial": the first `priority_pages` pages are indexed, so the document is
  already searchable while the rest keeps going.
- Resuming starts after `last_indexed_page`, so finished pages aren't
  embedded (and paid for) twice.
"""
import logging
import sqlite3
import threading
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timezone

from app.rag.config import rag_settings
from app.rag.errors import is_temporary_model_error
from app.rag.ingestion import open_pdf, read_pages, split_pages
from app.rag.vector_store import add_chunks, delete_document

logger = logging.getLogger(__name__)

# Statuses where no indexing is happening and the job can be resumed.
RESUMABLE = {"paused", "failed"}

_running: set[int] = set()
_running_lock = threading.Lock()


class JobAlreadyRunningError(RuntimeError):
    pass


def _connect() -> sqlite3.Connection:
    rag_settings.jobs_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(rag_settings.jobs_db)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS index_jobs (
            document_id INTEGER PRIMARY KEY,
            file_name TEXT,
            total_pages INTEGER,
            last_indexed_page INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            error TEXT,
            updated_at TEXT NOT NULL
        )"""
    )
    return conn


def get_job(document_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM index_jobs WHERE document_id = ?", (document_id,)).fetchone()
    if row is None:
        return None
    job = dict(row)
    job["running"] = is_running(document_id)
    return job


def _save(document_id: int, **fields) -> None:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    updates = ", ".join(f"{c} = excluded.{c}" for c in fields)
    with closing(_connect()) as conn, conn:
        conn.execute(
            f"INSERT INTO index_jobs (document_id, {columns}) VALUES (?, {placeholders}) "
            f"ON CONFLICT(document_id) DO UPDATE SET {updates}",
            (document_id, *fields.values()),
        )


def delete_job(document_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM index_jobs WHERE document_id = ?", (document_id,))


def is_running(document_id: int) -> bool:
    with _running_lock:
        return document_id in _running


def start_job(document_id: int, file_name: str | None, resume: bool = False) -> dict:
    """Register a job before it runs. Fresh start drops old chunks; resume keeps them.

    Raises JobAlreadyRunningError if this document is already being indexed.
    """
    with _running_lock:
        if document_id in _running:
            raise JobAlreadyRunningError(f"Document {document_id} is already being indexed")
        _running.add(document_id)  # reserved until run_job finishes

    job = get_job(document_id)
    if resume and job and job["status"] in RESUMABLE:
        _save(document_id, status="queued", error=None)
    else:
        delete_document(document_id)
        _save(document_id, file_name=file_name, total_pages=None, last_indexed_page=0, status="queued", error=None)
    return get_job(document_id)


def run_job(document_id: int, load_pdf: Callable[[], bytes]) -> None:
    """Index the document segment by segment. Must follow start_job(); safe to run in a background thread."""
    try:
        job = get_job(document_id)
        reader = open_pdf(load_pdf())
        total = len(reader.pages)
        first = job["last_indexed_page"] + 1
        _save(document_id, total_pages=total, status="partial" if first > rag_settings.priority_pages else "indexing")

        for start in range(first, total + 1, rag_settings.segment_pages):
            end = min(start + rag_settings.segment_pages - 1, total)
            chunks = split_pages(read_pages(reader, start, end), document_id, job["file_name"])
            add_chunks(document_id, chunks)
            if end == total:
                status = "completed"
            elif end >= rag_settings.priority_pages:
                status = "partial"
            else:
                status = "indexing"
            _save(document_id, last_indexed_page=end, status=status)
            logger.info("Document %s: pages %d-%d/%d indexed (%s)", document_id, start, end, total, status)
    except Exception as exc:
        status = "paused" if is_temporary_model_error(exc) else "failed"
        logger.warning("Document %s indexing %s: %s", document_id, status, exc)
        _save(document_id, status=status, error=str(exc)[:500])
    finally:
        with _running_lock:
            _running.discard(document_id)


def mark_interrupted_jobs() -> None:
    """On startup: jobs left mid-run by a restart can't be running anymore -> paused (resumable)."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE index_jobs SET status = 'paused', error = 'Interrupted by server restart' "
            "WHERE status IN ('queued', 'indexing', 'partial')"
        )
