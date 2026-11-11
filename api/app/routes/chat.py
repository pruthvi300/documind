"""
Chat with documents.

POST /api/chat          → full answer as JSON
POST /api/chat/stream   → Server-Sent Events:
    data: {"type": "token", "content": "..."}               (many)
    data: {"type": "sources", "sources": [...]}              (once)
    data: {"type": "done", "conversation_id": "..."}         (once, last)
    data: {"type": "error", "error": "..."}                  (instead of done, on failure)
Both endpoints store the question and answer in the conversation.
"""

import json
import logging
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session, get_db
from app.core.dependencies import get_rag_pipeline
from app.models.conversation import Conversation
from app.models.document import utcnow
from app.models.message import Message
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_pipeline import RAGPipeline

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])
settings = get_settings()


async def _load_history(db: AsyncSession, conversation_id: uuid.UUID | None) -> list[dict]:
    """Return recent messages, or [] for a new conversation. 404 if the id is unknown."""
    if conversation_id is None:
        return []
    exists = await db.scalar(
        select(Conversation.id).where(Conversation.id == conversation_id, Conversation.is_active.is_(True))
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    recent = (
        await db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(settings.HISTORY_MESSAGES)
        )
    ).all()
    return [{"role": m.role, "content": m.content} for m in reversed(recent)]


async def _save_exchange(
    db: AsyncSession,
    conversation_id: uuid.UUID | None,
    question: str,
    answer: str,
    sources: list,
    tokens: int | None,
) -> uuid.UUID:
    now = utcnow()
    if conversation_id is None:
        conversation = Conversation(title=question[:100], created_at=now, updated_at=now)
        db.add(conversation)
        await db.flush()
        conversation_id = conversation.id
    else:
        conversation = await db.get(Conversation, conversation_id)
        conversation.updated_at = now
    db.add(Message(conversation_id=conversation_id, role="user", content=question, created_at=now))
    db.add(
        Message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            sources=[s.model_dump() for s in sources],
            tokens_used=tokens,
            model_used=settings.active_model,
            # Strictly later than the question so history always replays in order.
            created_at=now + timedelta(microseconds=1),
        )
    )
    await db.commit()
    return conversation_id


def _doc_ids(request: ChatRequest) -> list[str] | None:
    return [str(d) for d in request.document_ids] if request.document_ids else None


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db), rag: RAGPipeline = Depends(get_rag_pipeline)):
    history = await _load_history(db, request.conversation_id)
    prepared = await rag.prepare(request.question, _doc_ids(request), history)
    answer, tokens = await rag.answer(prepared)
    conversation_id = await _save_exchange(
        db, request.conversation_id, request.question, answer, prepared.sources, tokens
    )
    return ChatResponse(
        answer=answer,
        sources=prepared.sources,
        conversation_id=conversation_id,
        tokens_used=tokens,
        model=settings.active_model,
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/stream")
async def chat_stream(
    request: ChatRequest, db: AsyncSession = Depends(get_db), rag: RAGPipeline = Depends(get_rag_pipeline)
):
    # Validate and retrieve before streaming starts, so errors are normal HTTP errors.
    history = await _load_history(db, request.conversation_id)
    prepared = await rag.prepare(request.question, _doc_ids(request), history)

    async def events():
        parts: list[str] = []
        try:
            async for token in rag.stream(prepared):
                parts.append(token)
                yield _sse({"type": "token", "content": token})
            yield _sse({"type": "sources", "sources": [s.model_dump() for s in prepared.sources]})
            # The request-scoped session may already be closed once streaming starts; use a fresh one.
            async with async_session() as session:
                conversation_id = await _save_exchange(
                    session, request.conversation_id, request.question, "".join(parts), prepared.sources, None
                )
            yield _sse({"type": "done", "conversation_id": str(conversation_id)})
        except Exception:
            log.exception("Streaming chat failed")
            yield _sse({"type": "error", "error": "The model failed to answer. Check that the LLM is reachable."})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
