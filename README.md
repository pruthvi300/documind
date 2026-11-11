# 🧠 DocuMind — AI-Powered Document Intelligence Platform

[![CI](https://github.com/pruthvi300/documind/actions/workflows/ci.yml/badge.svg)](https://github.com/pruthvi300/documind/actions/workflows/ci.yml)

> Upload documents. Ask questions. Get AI-powered answers with source citations.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.2+-orange.svg)](https://langchain.com)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## ✨ Features

- 📄 **Document Upload** — PDF, DOCX, TXT, Markdown, and CSV
- 🔍 **Semantic Search** — AI-powered document search using vector embeddings
- 💬 **Chat Interface** — Natural language Q&A with your documents
- 📝 **Source Citations** — Answers cite numbered sources, with page numbers for PDFs
- 🔄 **Streaming Responses** — Token-by-token answers via SSE, saved to the conversation
- 💾 **Embedding Cache** — Redis memoizes embeddings so repeated text isn't re-embedded
- 🏠 **Run Locally FREE** — Ollama support for completely local/offline operation
- 🐳 **Dockerized** — One command to start the entire stack

---

## 🏗️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | FastAPI + Uvicorn | Async API server |
| **AI/RAG** | LangChain + ChromaDB | RAG pipeline + vector search |
| **LLM** | OpenAI GPT-4o / Ollama Llama 3.1 | Text generation |
| **Embeddings** | text-embedding-3-small / nomic-embed-text | Document vectorization |
| **Database** | PostgreSQL | Document & conversation metadata |
| **Cache** | Redis | Embedding cache |
| **Frontend** | Next.js 14 (App Router) | SSR, file-based routing, streaming |
| **DevOps** | Docker Compose | Container orchestration |

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/pruthvi300/documind.git
cd documind
cp .env.example .env
# Edit .env with your OpenAI API key (or use Ollama for free)
docker compose up --build
```

To use Ollama instead of OpenAI, run it on your machine (`ollama serve`, then `ollama pull llama3.1:8b` and `ollama pull nomic-embed-text`). The API container reaches it through `host.docker.internal:11434`.

**Access:**
- 🌐 Frontend: http://localhost:3000
- 📡 API: http://localhost:8000
- 📖 Swagger Docs: http://localhost:8000/docs

### Option 2: Local Development

```bash
# Terminal 1: Backend
cd api
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env            # edit DATABASE_URL etc.
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm run dev

# Optional: Use Ollama for FREE local LLMs
ollama serve
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents/upload` | Upload & index a document |
| `GET` | `/api/documents` | List all documents |
| `GET` | `/api/documents/{id}` | Get document details |
| `DELETE` | `/api/documents/{id}` | Delete document + vectors |
| `POST` | `/api/chat` | Ask a question |
| `POST` | `/api/chat/stream` | Ask with streaming response |
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/conversations/{id}` | Get conversation messages |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation |
| `GET` | `/health` | Health check |

---

## 📁 Project Structure

```
documind/
├── api/                          # FastAPI Backend
│   ├── app/
│   │   ├── core/                 # Configuration, dependencies
│   │   │   ├── config.py         # Environment settings
│   │   │   ├── database.py       # PostgreSQL async connection
│   │   │   └── dependencies.py   # FastAPI dependency injection
│   │   ├── models/               # SQLAlchemy models
│   │   │   ├── document.py       # Document model
│   │   │   ├── conversation.py   # Conversation model
│   │   │   └── message.py        # Message model
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   │   ├── document.py
│   │   │   ├── chat.py
│   │   │   └── conversation.py
│   │   ├── routes/               # API route handlers
│   │   │   ├── documents.py      # Document CRUD endpoints
│   │   │   ├── chat.py           # Chat & streaming endpoints
│   │   │   └── conversations.py  # Conversation management
│   │   ├── services/             # Business logic
│   │   │   ├── document_processor.py  # Text extraction, chunking
│   │   │   ├── rag_pipeline.py   # RAG: retrieve, augment, generate
│   │   │   ├── vector_store.py   # ChromaDB operations
│   │   │   ├── embedding_cache.py # Redis embedding memoization
│   │   │   └── llm_factory.py    # OpenAI/Ollama provider
│   │   ├── utils/                # Helper utilities
│   │   │   └── text_processing.py
│   │   └── main.py               # FastAPI application entry
│   ├── tests/                    # pytest (fake LLM + embeddings, SQLite, fakeredis)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                     # Next.js Frontend (App Router)
│   ├── app/
│   │   ├── layout.js             # Root layout (Server Component)
│   │   ├── page.js               # Home — chat interface
│   │   ├── globals.css            # Global styles
│   │   ├── lib/api.js             # Upload/delete/stream helpers
│   │   ├── documents/
│   │   │   ├── page.js            # Documents page (SSR)
│   │   │   └── loading.js         # Auto loading state
│   │   └── components/
│   │       ├── ChatInterface.js   # Chat UI (Client Component)
│   │       ├── DocumentUpload.js  # Upload dropzone
│   │       └── DocumentList.js    # Document grid
│   ├── next.config.js             # API proxy config
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── docs/DESIGN.md                # Architecture and design decisions
└── README.md
```

---

## 🧠 How RAG Works

```
1. INGEST: File → Extract text per page → Chunk (500 chars) → Embed (Redis cache) → ChromaDB
2. QUERY:  Question (+ previous question) → Embed → Vector Search → Top 5 chunks above the relevance threshold
3. ANSWER: Numbered chunks + history + question → LLM → Streaming answer + citations
```

---

More detail on the pipeline, data model and design decisions is in [docs/DESIGN.md](docs/DESIGN.md).

---

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `openai` or `ollama` |
| `OPENAI_API_KEY` | - | Required if using OpenAI |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `OLLAMA_MODEL` | `llama3.1:8b` | Ollama model name |
| `EMBEDDING_PROVIDER` | `ollama` | `openai` or `ollama` |
| `OPENAI_EMBEDDING_MODEL` / `OLLAMA_EMBEDDING_MODEL` | `text-embedding-3-small` / `nomic-embed-text` | Embedding model |
| `CHUNK_SIZE` | `500` | Document chunk size (chars) |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `TOP_K_RESULTS` | `5` | Number of chunks to retrieve |
| `MIN_RELEVANCE_SCORE` | `0.3` | Drop chunks below this cosine relevance |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Embedding cache; empty disables it |

---

## 🧪 Testing

```bash
cd api
pip install -r requirements-dev.txt
pytest          # 19 tests, no Ollama/OpenAI/Postgres/Redis needed
ruff check app tests
```

> **Note:** there is no authentication. Anyone who can reach the API can read and delete every document.

---

## 📝 License

[MIT](LICENSE)

---

## 👨‍💻 Author

**Pruthviraj Kakade** — Full Stack Developer  
- GitHub: [github.com/pruthvi300](https://github.com/pruthvi300)
- LinkedIn: [linkedin.com/in/pruthviraj-kakade-631742169](https://linkedin.com/in/pruthviraj-kakade-631742169)
