"""
Redis-backed memoization for embeddings.

Embedding the same text twice (re-uploading a file, asking the same question)
returns the stored vector instead of calling the embedding model again. Keys
include the model name, so switching models never returns stale vectors.
Redis errors are logged and fall through to the real model.
"""

import hashlib
import json
import logging

import redis
from langchain_core.embeddings import Embeddings

log = logging.getLogger(__name__)


class CachedEmbeddings(Embeddings):
    def __init__(self, inner: Embeddings, client: "redis.Redis", namespace: str, ttl_seconds: int):
        self.inner = inner
        self.client = client
        self.namespace = namespace
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    def _key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"emb:{self.namespace}:{digest}"

    def _get_many(self, texts: list[str]) -> list[list[float] | None]:
        try:
            raw = self.client.mget([self._key(t) for t in texts])
        except redis.RedisError:
            log.warning("Embedding cache unavailable; calling the model directly")
            return [None] * len(texts)
        return [json.loads(r) if r else None for r in raw]

    def _set_many(self, texts: list[str], vectors: list[list[float]]) -> None:
        try:
            pipe = self.client.pipeline(transaction=False)
            for text, vector in zip(texts, vectors, strict=True):
                pipe.setex(self._key(text), self.ttl, json.dumps(vector))
            pipe.execute()
        except redis.RedisError:
            log.warning("Embedding cache unavailable; vectors not cached")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        cached = self._get_many(texts)
        missing = [i for i, v in enumerate(cached) if v is None]
        self.hits += len(texts) - len(missing)
        self.misses += len(missing)
        if missing:
            fresh = self.inner.embed_documents([texts[i] for i in missing])
            self._set_many([texts[i] for i in missing], fresh)
            for i, vector in zip(missing, fresh, strict=True):
                cached[i] = vector
        return cached  # type: ignore[return-value]

    def embed_query(self, text: str) -> list[float]:
        # Separate key space: some models embed queries and documents differently.
        key_text = "\x00query\x00" + text
        (cached,) = self._get_many([key_text])
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        vector = self.inner.embed_query(text)
        self._set_many([key_text], [vector])
        return vector
