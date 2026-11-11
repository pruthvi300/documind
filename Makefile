# DocuMind Makefile
# Quick commands for development

.PHONY: help setup run test docker clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ──

setup: ## Set up the development environment
	@echo "🧠 Setting up DocuMind..."
	cd api && python3 -m venv venv && ./venv/bin/pip install -r requirements-dev.txt
	cp .env.example .env
	@echo "✅ Setup complete! Edit .env with your settings."

setup-ollama: ## Install and set up Ollama (free local LLMs)
	@echo "📦 Installing Ollama..."
	curl -fsSL https://ollama.com/install.sh | sh
	ollama pull llama3.1:8b
	ollama pull nomic-embed-text
	@echo "✅ Ollama ready! Models downloaded."

# ── Development ──

run: ## Run the FastAPI server locally
	cd api && uvicorn app.main:app --reload --port 8000

run-frontend: ## Run the React frontend (if set up)
	cd frontend && npm run dev

# ── Docker ──

docker: ## Start all services with Docker Compose
	docker compose up --build

docker-down: ## Stop all Docker services
	docker compose down

docker-clean: ## Stop and remove all data (fresh start)
	docker compose down -v

# ── Database ──

db-create: ## Create database tables (the API also does this on startup)
	cd api && python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"

# ── Testing ──

test: ## Run all tests
	cd api && python -m pytest tests/ -v


# ── Utilities ──

clean: ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf api/uploads/* api/chroma_data/* 2>/dev/null || true
	@echo "🧹 Cleaned!"

lint: ## Run linting
	cd api && ruff check app tests
