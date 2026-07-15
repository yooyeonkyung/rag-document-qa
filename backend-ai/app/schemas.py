from pydantic import BaseModel


class IngestRequest(BaseModel):
    # Spring's `documents.id` - the correlation key back to MySQL.
    document_id: int
    # S3 URL from Spring's S3UploadService.upload(). Spring's current
    # POST /api/documents response is just a bare id and does NOT include
    # this yet - see phases/03-open-questions.md.
    file_url: str
    file_name: str | None = None


class IngestResponse(BaseModel):
    document_id: int
    file_name: str | None
    text: str
