import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="documind-test-")
os.environ.update(
    DATABASE_URL="sqlite+aiosqlite:///:memory:",
    REDIS_URL="",
    UPLOAD_DIR=os.path.join(_tmp, "uploads"),
    CHROMA_PERSIST_DIR=os.path.join(_tmp, "chroma"),
    MIN_RELEVANCE_SCORE="0.0",
    CHUNK_SIZE="200",
    CHUNK_OVERLAP="20",
)

import itertools  # noqa: E402
import uuid  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from langchain_core.embeddings import DeterministicFakeEmbedding  # noqa: E402
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.routes.chat as chat_routes  # noqa: E402
from app.core import database  # noqa: E402
from app.core.dependencies import get_llm, get_vector_store  # noqa: E402
from app.main import app  # noqa: E402
from app.services.vector_store import VectorStoreService  # noqa: E402

ANSWER = "The refund window is 30 days [1]."


class RecordingFakeChat(GenericFakeChatModel):
    """Fake LLM that always gives ANSWER and remembers the prompts it was sent."""

    calls: list = []

    def _generate(self, messages, *args, **kwargs):
        self.calls.append(messages)
        return super()._generate(messages, *args, **kwargs)


@pytest_asyncio.fixture
async def client(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        from app.models import conversation, document, message  # noqa: F401

        await conn.run_sync(database.Base.metadata.create_all)

    async def override_db():
        async with session_factory() as session:
            yield session

    # The streaming route opens its own session after the response starts.
    monkeypatch.setattr(chat_routes, "async_session", session_factory)

    store = VectorStoreService(
        DeterministicFakeEmbedding(size=32), persist_dir=None, collection_name=f"test_{uuid.uuid4().hex}"
    )
    llm = RecordingFakeChat(messages=itertools.repeat(ANSWER))
    llm.calls = []

    app.dependency_overrides[database.get_db] = override_db
    app.dependency_overrides[get_vector_store] = lambda: store
    app.dependency_overrides[get_llm] = lambda: llm
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.store, c.llm = store, llm
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()


async def upload(
    client, name="policy.txt", content=b"Refunds are accepted within 30 days of purchase.", mime="text/plain"
):
    return await client.post("/api/documents/upload", files={"file": (name, content, mime)})
