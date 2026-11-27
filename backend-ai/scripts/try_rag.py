"""
Run the RAG pipeline on a local PDF - no Spring, S3, or JWT needed.
Run from backend-ai/:

    # quick experiment: index only a page range (old chunks of the document are replaced)
    python -m scripts.try_rag ../file/s3-userguide.pdf --pages 1-30 --document-id 1

    # whole document as a resumable job (same runner as the API), then --resume if it paused
    python -m scripts.try_rag ../file/ec2-ug.pdf --document-id 3 --index-only
    python -m scripts.try_rag ../file/ec2-ug.pdf --document-id 3 --index-only --resume

    # ask without re-indexing
    python -m scripts.try_rag --document-id 1 --skip-index -q "How do I create a bucket?"

Without -q / --index-only it opens an interactive question loop (empty line to quit).
"""
import argparse
import logging
from pathlib import Path

from app.rag import jobs
from app.rag.ingestion import load_pdf_pages, split_pages
from app.rag.qa import answer_question
from app.rag.vector_store import index_document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdf", nargs="?", type=Path, help="PDF to index (omit with --skip-index)")
    parser.add_argument("--document-id", type=int, default=1)
    parser.add_argument("--pages", default=None, help="index only this 1-based inclusive range, e.g. 1-30")
    parser.add_argument("--resume", action="store_true", help="continue a paused/failed whole-document job")
    parser.add_argument("--skip-index", action="store_true", help="reuse what's already in Chroma")
    parser.add_argument("--index-only", action="store_true", help="index and exit without asking")
    parser.add_argument("-q", "--question", help="ask once and exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.skip_index:
        if args.pdf is None:
            parser.error("a PDF path is required unless --skip-index is given")
        if args.pages:
            first, _, last = args.pages.partition("-")
            pages = load_pdf_pages(args.pdf.read_bytes(), int(first), int(last) if last else None)
            chunks = split_pages(pages, args.document_id, args.pdf.name)
            print(f"Indexing {len(pages)} pages -> {len(chunks)} chunks (document_id={args.document_id})...")
            index_document(args.document_id, chunks)
            print("Done.\n")
        else:
            jobs.start_job(args.document_id, args.pdf.name, resume=args.resume)
            jobs.run_job(args.document_id, args.pdf.read_bytes)  # foreground here; the API runs it in the background
            job = jobs.get_job(args.document_id)
            print(f"Indexing {job['status']}: pages 1-{job['last_indexed_page']} of {job['total_pages']} indexed")
            if job["error"]:
                print(f"Error: {job['error']}")
            print()

    if args.index_only:
        return

    # The interactive loop keeps chat history, so follow-up questions work.
    history: list[dict] = []
    questions = [args.question] if args.question else iter(lambda: input("질문> ").strip(), "")
    for question in questions:
        result = answer_question(args.document_id, question, history)
        if result["search_query"] != question:
            print(f"(검색 질문: {result['search_query']})")
        pages = ", ".join(f"p.{s['page']}" for s in result["sources"])
        print(f"\n{result['answer']}\n출처: {pages}\n")
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": result["answer"]}]


if __name__ == "__main__":
    main()
