from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import UTCDatetime


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    uploaded_at: UTCDatetime
    processed_at: UTCDatetime | None = None


class DocumentUploadResponse(DocumentListItem):
    pass


class DocumentDetail(DocumentListItem):
    original_filename: str
    error_message: str | None = None
    is_active: bool


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int
