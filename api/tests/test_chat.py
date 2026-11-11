import json
import uuid

from langchain_core.messages import AIMessage

from tests.conftest import ANSWER, upload

QUESTION = "Refunds are accepted within 30 days of purchase."  # identical text → top hit with fake embeddings


def parse_sse(body: str) -> list[dict]:
    return [json.loads(line[len("data: ") :]) for line in body.splitlines() if line.startswith("data: ")]


async def test_chat_answers_with_sources_and_persists(client):
    await upload(client)
    response = await client.post("/api/chat", json={"question": QUESTION})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == ANSWER
    assert body["sources"][0]["document"] == "policy.txt"

    conversation = (await client.get(f"/api/conversations/{body['conversation_id']}")).json()
    assert [m["role"] for m in conversation["messages"]] == ["user", "assistant"]


async def test_follow_up_sends_history_as_ai_messages(client, monkeypatch):
    from app.core.config import get_settings

    # Fake embeddings are random, so a reworded follow-up can score below zero.
    monkeypatch.setattr(get_settings(), "MIN_RELEVANCE_SCORE", -1.0)
    await upload(client)
    first = (await client.post("/api/chat", json={"question": QUESTION})).json()
    await client.post(
        "/api/chat", json={"question": "And for sale items?", "conversation_id": first["conversation_id"]}
    )

    prompt = client.llm.calls[-1]
    assert any(isinstance(m, AIMessage) and m.content == ANSWER for m in prompt)
    assert prompt[-1].content == "And for sale items?"


async def test_unknown_conversation_is_404(client):
    await upload(client)
    response = await client.post("/api/chat", json={"question": "hi", "conversation_id": str(uuid.uuid4())})
    assert response.status_code == 404


async def test_no_documents_skips_the_llm(client):
    response = await client.post("/api/chat", json={"question": "anything"})
    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert client.llm.calls == []


async def test_document_filter(client):
    await upload(client)
    response = await client.post("/api/chat", json={"question": QUESTION, "document_ids": [str(uuid.uuid4())]})
    assert response.json()["sources"] == []


async def test_stream_event_protocol_and_persistence(client):
    await upload(client)
    response = await client.post("/api/chat/stream", json={"question": QUESTION})
    assert response.status_code == 200
    events = parse_sse(response.text)

    tokens = [e["content"] for e in events if e["type"] == "token"]
    assert "".join(tokens) == ANSWER
    assert [e["type"] for e in events][-2:] == ["sources", "done"]
    assert events[-2]["sources"][0]["document"] == "policy.txt"

    conversation_id = events[-1]["conversation_id"]
    stored = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert stored["messages"][1]["content"] == ANSWER

    listing = (await client.get("/api/conversations")).json()
    assert listing[0]["message_count"] == 2


async def test_stream_unknown_conversation_is_plain_404(client):
    response = await client.post("/api/chat/stream", json={"question": "x", "conversation_id": str(uuid.uuid4())})
    assert response.status_code == 404


async def test_delete_conversation(client):
    await upload(client)
    conversation_id = (await client.post("/api/chat", json={"question": QUESTION})).json()["conversation_id"]
    assert (await client.delete(f"/api/conversations/{conversation_id}")).status_code == 204
    assert (await client.get(f"/api/conversations/{conversation_id}")).status_code == 404
