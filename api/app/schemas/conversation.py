from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import UTCDatetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    sources: list | None = None
    tokens_used: int | None = None
    model_used: str | None = None
    created_at: UTCDatetime


class ConversationListItem(BaseModel):
    id: UUID
    title: str
    created_at: UTCDatetime
    updated_at: UTCDatetime
    message_count: int = 0


class ConversationDetail(BaseModel):
    id: UUID
    title: str
    created_at: UTCDatetime
    updated_at: UTCDatetime
    messages: list[MessageResponse]
