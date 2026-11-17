from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    # Spring's `documents.id` - the correlation key back to MySQL.
    document_id: int
    # S3 URL from Spring's S3UploadService.upload(). Spring's current
    # POST /api/documents response is just a bare id and does NOT include
    # this yet - see phases/03-open-questions.md.
    file_url: str
    file_name: str | None = None


class PageText(BaseModel):
    # 1-based, matching what a PDF viewer shows - used later to cite sources
    # and stored as `document_chunks.page_number`.
    page_number: int
    text: str


class IngestResponse(BaseModel):
    document_id: int
    file_name: str | None
    # Only pages with extractable text; image-only pages are skipped.
    pages: list[PageText]


class ChatRequest(BaseModel):
    document_id: int
    question: str = Field(min_length=1)


class Source(BaseModel):
    page: int


class ChatResponse(BaseModel):
    answer: str
    # Pages of the chunks the answer was built from, ascending.
    sources: list[Source]
