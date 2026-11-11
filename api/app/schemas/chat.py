from uuid import UUID

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    document: str
    document_id: str | None = None
    chunk_text: str
    chunk_index: int
    relevance_score: float
    page_number: int | None = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: UUID | None = Field(None, description="Continue an existing conversation")
    document_ids: list[UUID] | None = Field(None, description="Limit search to these documents")


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    conversation_id: UUID
    tokens_used: int | None = None
    model: str
