import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationDetail, ConversationListItem, MessageResponse

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])
Db = Annotated[AsyncSession, Depends(get_db)]


async def _get_active(db: AsyncSession, conversation_id: uuid.UUID) -> Conversation:
    conversation = await db.scalar(
        select(Conversation).where(Conversation.id == conversation_id, Conversation.is_active.is_(True))
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("", response_model=list[ConversationListItem])
async def list_conversations(db: Db, skip: int = 0, limit: int = 20):
    """Most recently updated first, with message counts in a single query."""
    limit = max(1, min(limit, 100))
    counts = (
        select(Message.conversation_id, func.count(Message.id).label("n")).group_by(Message.conversation_id).subquery()
    )
    rows = await db.execute(
        select(Conversation, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.conversation_id == Conversation.id)
        .where(Conversation.is_active.is_(True))
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return [
        ConversationListItem(id=c.id, title=c.title, created_at=c.created_at, updated_at=c.updated_at, message_count=n)
        for c, n in rows.all()
    ]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: uuid.UUID, db: Db):
    conversation = await _get_active(db, conversation_id)
    messages = (
        await db.scalars(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
        )
    ).all()
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: uuid.UUID, db: Db):
    conversation = await _get_active(db, conversation_id)
    conversation.is_active = False
    await db.commit()
