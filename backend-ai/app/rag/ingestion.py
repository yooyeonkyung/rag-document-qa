"""
PDF bytes -> one Document per page -> chunks that never cross a page boundary.
"""
import io

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.rag.config import rag_settings


def open_pdf(pdf_bytes: bytes) -> PdfReader:
    return PdfReader(io.BytesIO(pdf_bytes))


def load_pdf_pages(pdf_bytes: bytes, first_page: int = 1, last_page: int | None = None) -> list[Document]:
    """Extract text per page (1-based, inclusive range). Pages with no text are skipped."""
    return read_pages(open_pdf(pdf_bytes), first_page, last_page)


def read_pages(reader: PdfReader, first_page: int = 1, last_page: int | None = None) -> list[Document]:
    """Same as load_pdf_pages, but reuses an open reader (large PDFs are read segment by segment)."""
    last_page = min(last_page or len(reader.pages), len(reader.pages))
    pages = []
    for page_number in range(first_page, last_page + 1):
        text = reader.pages[page_number - 1].extract_text() or ""
        if text.strip():
            pages.append(Document(page_content=text, metadata={"page": page_number}))
    return pages


def split_pages(pages: list[Document], document_id: int, file_name: str | None = None) -> list[Document]:
    """Split each page on its own, tagging chunks with document_id/page for filtering and citations."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=rag_settings.chunk_size,
        chunk_overlap=rag_settings.chunk_overlap,
    )
    chunks = []
    for page in pages:
        for index, text in enumerate(splitter.split_text(page.page_content)):
            metadata = {"document_id": document_id, "page": page.metadata["page"], "chunk_index": index}
            if file_name:  # Chroma metadata can't hold None
                metadata["file_name"] = file_name
            chunks.append(Document(page_content=text, metadata=metadata))
    return chunks
