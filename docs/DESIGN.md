# DocuMind — Design Notes

How DocuMind works and why it is built this way. For setup, see the [README](../README.md).

## Overview

**DocuMind** is an AI-powered document intelligence platform that lets users upload documents and have natural language conversations with their content. It demonstrates production-grade RAG (Retrieval-Augmented Generation) architecture, combining modern full-stack development with cutting-edge AI technologies.

**Problem Statement:** Organizations have thousands of documents (PDFs, reports, policies) but finding specific information requires reading entire documents manually. How do you make document knowledge instantly accessible through natural language?

**Solution:** A RAG pipeline using LangChain + ChromaDB for semantic document search, FastAPI for high-performance async API, and a React frontend for real-time chat with streaming AI responses.

## 🏗️ Architecture Deep Dive

### High-Level System Design

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        DocuMind Architecture                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│    ┌──────────────┐                                                      │
│    │   User        │                                                      │
│    │   Browser     │                                                      │
│    └───────┬──────┘                                                      │
│            │                                                              │
│            ▼                                                              │
│    ┌──────────────────────────────────────────────────────┐              │
│    │              NGINX / Reverse Proxy                    │              │
│    └────────────────────────┬─────────────────────────────┘              │
│                             │                                             │
│         ┌───────────────────┴───────────────────┐                        │
│         │                                       │                         │
│         ▼                                       ▼                         │
│    ┌─────────────┐                       ┌─────────────┐                 │
│    │  React SPA  │                       │  FastAPI    │                  │
│    │  Chat UI    │◀──── REST/SSE ──────▶│  (Uvicorn)  │                 │
│    │  Port: 5173 │                       │  Port: 8000 │                 │
│    └─────────────┘                       └──────┬──────┘                 │
│                                                  │                        │
│                     ┌────────────────────────────┼────────────────┐       │
│                     │                            │                │       │
│                     ▼                            ▼                ▼       │
│              ┌───────────┐              ┌───────────┐    ┌───────────┐  │
│              │  ChromaDB │              │PostgreSQL │    │   Redis   │  │
│              │ (Vectors) │              │ (Metadata)│    │  (Cache)  │  │
│              │  Persist  │              │ Port:5432 │    │ Port:6379 │  │
│              └─────┬─────┘              └───────────┘    └───────────┘  │
│                    │                                                      │
│                    ▼                                                      │
│              ┌───────────────────┐                                       │
│              │   LLM Provider    │                                       │
│              │ ┌───────────────┐ │                                       │
│              │ │ OpenAI GPT-4o │ │                                       │
│              │ │       OR      │ │                                       │
│              │ │ Ollama (Free) │ │                                       │
│              │ └───────────────┘ │                                       │
│              └───────────────────┘                                       │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### Request Flow: Document Upload (Ingestion)

```
User uploads: annual_report.pdf

1. Frontend sends multipart/form-data to POST /api/documents/upload
2. FastAPI validates the extension, then streams the file to disk (413 past MAX_FILE_SIZE_MB)
3. In a worker thread (so the event loop stays free):
   ├── Extract text per section: pypdf per page, python-docx, csv rows as "col: value", txt/md as-is
   ├── Split each section with RecursiveCharacterTextSplitter (500 chars, 50 overlap)
   │   → every chunk keeps the page number it came from
   ├── Embed chunks (Redis embedding cache first, then the model for misses)
   └── Store vectors + text + metadata in ChromaDB (cosine space)
4. Save the document row in PostgreSQL (status=indexed, chunk_count)
5. Failure: delete the saved file and any partial vectors, return 422 (no text) or 502 (model down)
```

### Request Flow: Chat Query (RAG Pipeline)

```
User asks: "What was the revenue growth in Q4?"

1. POST /api/chat (JSON answer) or POST /api/chat/stream (SSE)
2. Load the last 6 messages if conversation_id is given (404 if unknown)
3. RETRIEVE:
   ├── Search text = previous user question + this question (helps follow-ups)
   ├── Embed it and query ChromaDB for the top 5 chunks (optionally filtered by document_ids)
   └── Drop chunks below MIN_RELEVANCE_SCORE; if none remain, answer "not found" without calling the LLM
4. AUGMENT:
   └── System prompt with numbered sources [1]..[5] + history (as user/assistant turns) + question
5. GENERATE:
   ├── GPT-4o-mini or Llama 3.1, temperature 0
   └── Stream tokens, then send the sources, then save the exchange and send conversation_id
```

## 📊 Database Schema

### Entity Relationship Diagram

```
┌─────────────────────────────────────┐
│            DOCUMENTS                 │
├─────────────────────────────────────┤
│ id              UUID (PK)            │
│ filename        VARCHAR(255)         │
│ file_type       VARCHAR(20)          │  ◀── pdf, txt, md, csv
│ file_size       INTEGER              │
│ chunk_count     INTEGER              │  ◀── Denormalized counter
│ status          VARCHAR(20)          │  ◀── uploading, processing, indexed, failed
│ uploaded_at     TIMESTAMP            │
│ processed_at    TIMESTAMP            │
│ is_active       BOOLEAN              │
└─────────────────────────────────────┘
              │
              │ 1:N
              ▼
┌─────────────────────────────────────┐
│          CONVERSATIONS               │
├─────────────────────────────────────┤
│ id              UUID (PK)            │
│ title           VARCHAR(255)         │  ◀── Auto-generated or user-defined
│ created_at      TIMESTAMP            │
│ updated_at      TIMESTAMP            │
│ is_active       BOOLEAN              │
└─────────────────────────────────────┘
              │
              │ 1:N
              ▼
┌─────────────────────────────────────┐
│            MESSAGES                  │
├─────────────────────────────────────┤
│ id              UUID (PK)            │
│ conversation_id UUID (FK)            │  ◀── Index
│ role            VARCHAR(10)          │  ◀── user, assistant
│ content         TEXT                 │
│ sources         JSONB                │  ◀── Citation metadata
│ tokens_used     INTEGER              │
│ confidence      FLOAT                │
│ created_at      TIMESTAMP            │
└─────────────────────────────────────┘


┌─────────────────────────────────────┐
│     DOCUMENT_CONVERSATIONS           │
│          (Many-to-Many)              │
├─────────────────────────────────────┤
│ document_id     UUID (FK)            │
│ conversation_id UUID (FK)            │
│ PRIMARY KEY (document_id,            │
│              conversation_id)        │
└─────────────────────────────────────┘


Vector Store (ChromaDB - Separate):
┌─────────────────────────────────────┐
│          CHUNKS (ChromaDB)           │
├─────────────────────────────────────┤
│ id              STRING (PK)          │  ◀── "{doc_id}_chunk_{i}"
│ document        TEXT                 │  ◀── Chunk text content
│ embedding       FLOAT[1536]          │  ◀── Vector representation
│ metadata:                            │
│   ├── document_id  UUID              │
│   ├── filename     STRING            │
│   ├── chunk_index  INTEGER           │
│   ├── page_number  INTEGER           │
│   └── total_chunks INTEGER           │
└─────────────────────────────────────┘
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **ChromaDB for vectors** | Embedded, no separate server, perfect for MVP. Migrate to Pinecone/pgvector at scale |
| **PostgreSQL for metadata** | JSONB for flexible source citations, robust relational integrity |
| **Redis for caching** | Memoize embeddings by model + text hash; failures fall back to the model |
| **UUID primary keys** | No sequential ID guessing, safe for public APIs |
| **JSONB for sources** | Flexible citation format: file, page, chunk text, confidence |
| **Separate conversations table** | Multi-turn chat, conversation history management |
| **Many-to-many docs↔convos** | One conversation can reference multiple documents |

## 🔑 Key Technical Decisions

### 1. RAG Architecture (Retrieve → Augment → Generate)

**Why RAG over Fine-Tuning?**

| Approach | Pros | Cons |
|----------|------|------|
| **RAG** ✅ | No training needed, real-time data, traceable sources | Depends on retrieval quality |
| **Fine-tuning** | Better for domain-specific language | Expensive, needs training data, no source citations |

```python
# Our RAG pipeline implementation
class RAGPipeline:
    def __init__(self, vectorstore, llm):
        self.vectorstore = vectorstore
        self.llm = llm
    
    async def query(self, question: str, doc_ids: list[str] = None) -> RAGResponse:
        # 1. Retrieve relevant chunks
        retriever = self.vectorstore.as_retriever(
            search_kwargs={
                "k": 5,
                "filter": {"document_id": {"$in": doc_ids}} if doc_ids else None
            }
        )
        chunks = await retriever.aget_relevant_documents(question)
        
        # 2. Build augmented prompt
        context = "\n---\n".join([chunk.page_content for chunk in chunks])
        prompt = self._build_prompt(question, context)
        
        # 3. Generate with streaming
        async for token in self.llm.astream(prompt):
            yield token
```

### 2. Dual LLM Support (OpenAI + Ollama)

```python
# Provider factory pattern — switch between paid and free
class LLMFactory:
    @staticmethod
    def create(provider: str = "openai"):
        if provider == "openai":
            return ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True)
        elif provider == "ollama":
            return ChatOllama(model="llama3.1:8b", temperature=0)
        raise ValueError(f"Unknown provider: {provider}")
```

**Benefits:**
- Learn with Ollama (FREE, runs locally)
- Scale with OpenAI in production
- Same interface, swap with one config change

### 3. Streaming Responses via SSE

`POST /api/chat/stream` returns `text/event-stream` with one JSON object per event:

```
data: {"type": "token", "content": "Revenue"}
data: {"type": "token", "content": " grew"}
...
data: {"type": "sources", "sources": [{"document": "report.pdf", "page_number": 12, ...}]}
data: {"type": "done", "conversation_id": "…"}
```

Validation and retrieval happen *before* streaming starts, so a bad conversation id is an ordinary 404. Errors mid-stream arrive as `{"type": "error"}`. The exchange is saved with a fresh database session after the last token, because the request's session may already be closed once a streaming response has started.

**Why SSE over WebSockets?**
- Simpler for one-way streaming (server → client)
- Plain HTTP, so it works through proxies and load balancers
- The browser reads it with `fetch()` + a stream reader (POST body support, unlike `EventSource`)

### 4. Document Processing Pipeline

See `app/services/document_processor.py`. Text is extracted per section so chunks keep page numbers:

```python
def process_document(self, file_path, document_id, filename) -> int:
    sections = self.extract_sections(file_path)       # [Section(text, page_number)]
    if not sections:
        raise ValueError("No text could be extracted (is it a scanned PDF?)")
    chunks, metadatas = self.chunk_sections(sections)  # page_number carried per chunk
    return self.vector_store.add_documents(chunks, document_id, filename, metadatas)
```

The route runs this with `asyncio.to_thread`, because parsing and embedding calls block.

## 🚀 Performance Optimizations

### 1. Embedding Caching

`app/services/embedding_cache.py` wraps any LangChain `Embeddings` object:

```python
class CachedEmbeddings(Embeddings):
    def embed_documents(self, texts):
        cached = self._get_many(texts)                  # one Redis MGET
        missing = [i for i, v in enumerate(cached) if v is None]
        if missing:
            fresh = self.inner.embed_documents([texts[i] for i in missing])  # one batched model call
            self._set_many([texts[i] for i in missing], fresh)               # one pipelined SETEX
            ...
```

- Keys are `emb:<provider>:<model>:<sha256(text)>`, so switching models never returns stale vectors.
- Query embeddings use a separate key space (some models embed queries differently).
- If Redis is down, it logs a warning and calls the model directly.

The cache saves repeated embedding calls (re-uploads, repeated questions). It does not cache LLM answers. No latency or cost numbers have been measured yet.

### 2. Batch Embedding Generation

Chunks are embedded with one `embed_documents` call per upload rather than one call per chunk, and only cache misses are sent to the model.

### 3. Smart Retrieval with Metadata Filters

```python
# Without filter: Search ALL chunks across ALL documents
results = collection.query(query, n_results=5)  # Searches 100K+ chunks

# With filter: Only search relevant documents
results = collection.query(
    query, 
    n_results=5,
    where={"document_id": {"$in": selected_doc_ids}}
)  # Searches only 500 chunks — much faster and more relevant
```

## 🎨 Frontend Architecture

### Next.js 14 App Router

- `app/page.js` (server) renders `ChatInterface` (client component).
- `app/documents/page.js` is a **server component** that fetches the document list on the server; upload and delete call `router.refresh()` to re-run it.
- `next.config.js` rewrites `/api/*` to FastAPI, so the browser only talks to its own origin.

### Streaming chat (`app/lib/api.js`)

```js
const res = await fetch('/api/chat/stream', { method: 'POST', body: JSON.stringify({ question, conversation_id }) });
const reader = res.body.getReader();
let buffer = '';
for (;;) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const events = buffer.split('\n\n');
  buffer = events.pop();                 // keep a partial event for the next read
  for (const e of events) onEvent(JSON.parse(e.slice(6)));
}
```

The `done` event's `conversation_id` is kept in state, so follow-up questions continue the same conversation.

### Technology Choices

| Technology | Purpose | Why? |
|------------|---------|------|
| Next.js 14 (App Router) | Framework | Server components for the document list, client components for chat |
| React Markdown | Rendering | AI answers often contain markdown |
| react-dropzone | Upload | Drag-and-drop with type filtering |
| fetch + ReadableStream | Streaming | SSE over POST |

## 🐳 Docker & DevOps

### Docker Compose Services

```yaml
services:
  api:           # FastAPI backend; ChromaDB runs embedded with a persistent volume
  postgres:      # Document and conversation metadata
  redis:         # Embedding cache
  frontend:      # Next.js dev server
```

### Environment Configuration

```env
# .env.example
# LLM Provider (openai or ollama)
LLM_PROVIDER=ollama
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=postgresql+asyncpg://documind:password@postgres:5432/documind

# Redis
REDIS_URL=redis://redis:6379/0

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_data

# Ollama (if using local models)
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents/upload` | Upload & index a document |
| `GET` | `/api/documents` | List all documents |
| `GET` | `/api/documents/{id}` | Get document details |
| `DELETE` | `/api/documents/{id}` | Delete document & vectors |
| `POST` | `/api/chat` | Send question, get answer |
| `POST` | `/api/chat/stream` | Send question, stream answer (SSE) |
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/conversations/{id}` | Get conversation history |
| `DELETE` | `/api/conversations/{id}` | Delete conversation |
| `GET` | `/health` | Health check |

### Request/Response Examples

```json
// POST /api/documents/upload
// Request: multipart/form-data with file

// Response:
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "annual_report.pdf",
    "file_type": "pdf",
    "file_size": 2456789,
    "chunk_count": 47,
    "status": "indexed",
    "uploaded_at": "2026-03-05T19:45:00Z"
}
```

```json
// POST /api/chat
// Request:
{
    "question": "What was the revenue in Q4?",
    "conversation_id": "optional-uuid-for-follow-ups",
    "document_ids": ["doc-uuid-1", "doc-uuid-2"]
}

// Response:
{
    "answer": "According to the annual report, Q4 revenue was $12.5M, representing a 15% year-over-year growth...",
    "sources": [
        {
            "document": "annual_report.pdf",
            "page": 12,
            "chunk": "...Q4 revenue reached $12.5 million...",
            "relevance_score": 0.94
        }
    ],
    "conversation_id": "conv-uuid",
    "tokens_used": 847,
    "model": "gpt-4o-mini"
}
```
