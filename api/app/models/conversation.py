import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.document import utcnow

# Many-to-many: a conversation can be scoped to several documents.
document_conversations = Table(
    "document_conversations",
    Base.metadata,
    Column("document_id", Uuid, ForeignKey("documents.id"), primary_key=True),
    Column("conversation_id", Uuid, ForeignKey("conversations.id"), primary_key=True),
)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), default="New Conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")
    documents = relationship("Document", secondary=document_conversations)
