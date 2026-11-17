"""
Run the RAG pipeline on a local PDF - no Spring, S3, or JWT needed.
Run from backend-ai/:

    python -m scripts.try_rag ../file/s3-userguide.pdf --pages 1-30 --document-id 1
    python -m scripts.try_rag --document-id 1 --skip-index -q "버킷을 만드는 방법은?"

Without -q it opens an interactive question loop (empty line to quit).
"""
import argparse
from pathlib import Path

from app.rag.ingestion import load_pdf_pages, split_pages
from app.rag.qa import answer_question
from app.rag.vector_store import index_document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdf", nargs="?", type=Path, help="PDF to index (omit with --skip-index)")
    parser.add_argument("--document-id", type=int, default=1)
    parser.add_argument("--pages", default=None, help="1-based inclusive range like 1-30 (default: all)")
    parser.add_argument("--skip-index", action="store_true", help="reuse what's already in Chroma")
    parser.add_argument("-q", "--question", help="ask once and exit")
    args = parser.parse_args()

    if not args.skip_index:
        if args.pdf is None:
            parser.error("a PDF path is required unless --skip-index is given")
        first, _, last = (args.pages or "1-").partition("-")
        pages = load_pdf_pages(args.pdf.read_bytes(), int(first), int(last) if last else None)
        chunks = split_pages(pages, args.document_id, args.pdf.name)
        print(f"Indexing {len(pages)} pages -> {len(chunks)} chunks (document_id={args.document_id})...")
        index_document(args.document_id, chunks)
        print("Done.\n")

    questions = [args.question] if args.question else iter(lambda: input("질문> ").strip(), "")
    for question in questions:
        result = answer_question(args.document_id, question)
        print(f"\n{result['answer']}\n출처: {', '.join(f'p.{s['page']}' for s in result['sources'])}\n")


if __name__ == "__main__":
    main()
