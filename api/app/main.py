"""DocuMind API entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.dependencies import get_vector_store
from app.routes import chat, conversations, documents
from app.services.llm_factory import provider_info
from app.services.vector_store import VectorStoreService

settings = get_settings()
logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)
log = logging.getLogger("documind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "Starting %s v%s (LLM: %s/%s)",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.LLM_PROVIDER,
        settings.active_model,
    )
    await init_db()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    description="Upload documents and chat with them using Retrieval-Augmented Generation.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(conversations.router)


@app.get("/health", tags=["System"])
async def health_check(vector_store: VectorStoreService = Depends(get_vector_store)):
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "llm": {
            "provider": settings.LLM_PROVIDER,
            "model": settings.active_model,
            **provider_info(settings.LLM_PROVIDER),
        },
        "vector_store": vector_store.get_collection_stats(),
    }


@app.get("/", tags=["System"])
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}", "docs": "/docs", "health": "/health"}
