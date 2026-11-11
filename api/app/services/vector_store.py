"""
ChromaDB access: store chunks, semantic search, delete by document.

All methods are blocking (embedding + Chroma calls). Async routes run them
in a worker thread so the event loop stays responsive.
"""

import logging

from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument
from langchain_core.embeddings import Embeddings

log = logging.getLogger(__name__)


class VectorStoreService:
    def __init__(self, embeddings: Embeddings, persist_dir: str | None, collection_name: str = "documind_chunks"):
        self.embeddings = embeddings
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=persist_dir,
            # Cosine distance gives relevance scores in [0, 1] regardless of vector norm.
            # Only applies when the collection is first created.
            collection_metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self, chunks: list[str], document_id: str, filename: str, metadatas: list[dict] | None = None
    ) -> int:
        documents = []
        for i, text in enumerate(chunks):
            metadata = {"document_id": document_id, "filename": filename, "chunk_index": i, "total_chunks": len(chunks)}
            if metadatas and i < len(metadatas):
                metadata.update(metadatas[i])
            documents.append(LCDocument(page_content=text, metadata=metadata))
        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        self.vectorstore.add_documents(documents=documents, ids=ids)
        return len(documents)

    def search(
        self, query: str, k: int = 5, document_ids: list[str] | None = None, min_score: float = 0.0
    ) -> list[dict]:
        kwargs: dict = {"k": k}
        if document_ids:
            kwargs["filter"] = {"document_id": {"$in": document_ids}}
        results = self.vectorstore.similarity_search_with_relevance_scores(query=query, **kwargs)
        return [
            {"content": doc.page_content, "metadata": doc.metadata, "relevance_score": round(score, 4)}
            for doc, score in results
            if score >= min_score
        ]

    def delete_document(self, document_id: str) -> None:
        self.vectorstore.delete(where={"document_id": document_id})

    def get_collection_stats(self) -> dict:
        try:
            return {"total_chunks": self.vectorstore._collection.count(), "collection_name": self.collection_name}
        except Exception as exc:  # health endpoint must not crash
            log.warning("Could not read Chroma stats: %s", exc)
            return {"total_chunks": None, "error": "unavailable"}
