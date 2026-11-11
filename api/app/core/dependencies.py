"""Process-wide singletons for the AI services. Tests override these with fakes."""

from functools import lru_cache

import redis
from fastapi import Depends
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import get_settings
from app.services.document_processor import DocumentProcessor
from app.services.embedding_cache import CachedEmbeddings
from app.services.llm_factory import create_chat_model, create_embeddings
from app.services.rag_pipeline import RAGPipeline
from app.services.vector_store import VectorStoreService


@lru_cache
def get_vector_store() -> VectorStoreService:
    settings = get_settings()
    embeddings = create_embeddings(settings)
    if settings.REDIS_URL:
        client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=0.5, socket_connect_timeout=0.5)
        namespace = f"{settings.EMBEDDING_PROVIDER}:{settings.active_embedding_model}"
        embeddings = CachedEmbeddings(embeddings, client, namespace, settings.EMBEDDING_CACHE_TTL_SECONDS)
    return VectorStoreService(embeddings=embeddings, persist_dir=settings.CHROMA_PERSIST_DIR)


@lru_cache
def get_llm():
    return create_chat_model(get_settings())


def get_rag_pipeline(
    vector_store: VectorStoreService = Depends(get_vector_store), llm: BaseChatModel = Depends(get_llm)
) -> RAGPipeline:
    settings = get_settings()
    return RAGPipeline(vector_store, llm, top_k=settings.TOP_K_RESULTS, min_score=settings.MIN_RELEVANCE_SCORE)


def get_document_processor(vector_store: VectorStoreService = Depends(get_vector_store)) -> DocumentProcessor:
    settings = get_settings()
    return DocumentProcessor(vector_store, chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
