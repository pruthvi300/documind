"""Provider pattern: build chat models and embeddings for OpenAI or Ollama."""

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

PROVIDERS = {"openai": {"name": "OpenAI", "type": "cloud"}, "ollama": {"name": "Ollama", "type": "local"}}


def _check(provider: str) -> None:
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Supported: {', '.join(PROVIDERS)}")


def create_chat_model(settings) -> BaseChatModel:
    _check(settings.LLM_PROVIDER)
    if settings.LLM_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for LLM_PROVIDER=openai (or use LLM_PROVIDER=ollama)")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
            max_tokens=settings.LLM_MAX_TOKENS,
            stream_usage=True,
        )
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
        num_predict=settings.LLM_MAX_TOKENS,
    )


def create_embeddings(settings) -> Embeddings:
    _check(settings.EMBEDDING_PROVIDER)
    if settings.EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY)
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(model=settings.OLLAMA_EMBEDDING_MODEL, base_url=settings.OLLAMA_BASE_URL)


def provider_info(provider: str) -> dict:
    return PROVIDERS.get(provider, {"name": "Unknown", "type": "unknown"})
