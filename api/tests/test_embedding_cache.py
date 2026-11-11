import fakeredis
import redis
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.services.embedding_cache import CachedEmbeddings


class CountingEmbeddings(DeterministicFakeEmbedding):
    calls: int = 0

    def embed_documents(self, texts):
        self.calls += len(texts)
        return super().embed_documents(texts)

    def embed_query(self, text):
        self.calls += 1
        return super().embed_query(text)


def test_repeated_texts_hit_the_cache():
    inner = CountingEmbeddings(size=8)
    cached = CachedEmbeddings(inner, fakeredis.FakeRedis(), "fake:model", ttl_seconds=60)

    first = cached.embed_documents(["a", "b"])
    second = cached.embed_documents(["b", "c"])
    assert inner.calls == 3  # "b" was served from Redis
    assert second[0] == first[1]
    assert (cached.hits, cached.misses) == (1, 3)

    cached.embed_query("a")
    cached.embed_query("a")
    assert inner.calls == 4


def test_namespace_isolates_models():
    client = fakeredis.FakeRedis()
    a = CachedEmbeddings(CountingEmbeddings(size=8), client, "model-a", 60)
    b_inner = CountingEmbeddings(size=8)
    b = CachedEmbeddings(b_inner, client, "model-b", 60)
    a.embed_documents(["x"])
    b.embed_documents(["x"])
    assert b_inner.calls == 1


def test_redis_outage_falls_back_to_model():
    class Broken(fakeredis.FakeRedis):
        def mget(self, *a, **k):
            raise redis.ConnectionError("down")

        def pipeline(self, *a, **k):
            raise redis.ConnectionError("down")

    inner = CountingEmbeddings(size=8)
    cached = CachedEmbeddings(inner, Broken(), "m", 60)
    assert len(cached.embed_documents(["x", "y"])) == 2
    assert inner.calls == 2
