"""
IndexManager — unified interface for adding and querying stores.
Vector backend (FAISS or Qdrant) + BM25 + optional LightRAG.
"""
from __future__ import annotations

import asyncio
import logging

from src.indexing.bm25_store import BM25Store
from src.config import FAISS_TOP_K, LIGHTRAG_TOP_K, BM25_TOP_K, VECTOR_BACKEND

logger = logging.getLogger(__name__)


def _make_vector_store():
    """Factory: return FAISSStore or QdrantStore based on config."""
    if VECTOR_BACKEND == "qdrant":
        from src.indexing.qdrant_store import QdrantStore
        return QdrantStore()
    else:
        from src.indexing.faiss_store import FAISSStore
        return FAISSStore()


async def _empty_coroutine() -> list:
    return []


class IndexManager:
    def __init__(self, use_lightrag: bool = True):
        self.vector = _make_vector_store()
        # Keep .faiss alias for backward compat (retriever/reranker reference it)
        self.faiss = self.vector
        self.bm25 = BM25Store()
        self._use_lightrag = use_lightrag
        if use_lightrag:
            from src.indexing.lightrag_store import LightRAGStore
            self.lightrag = LightRAGStore()
        else:
            self.lightrag = None

    def add(self, text: str, metadata: dict) -> None:
        """
        Add a single chunk to both indexes.
        Runs LightRAG in async event loop.
        """
        self.vector.add(text, metadata)

        # LightRAG is async — run in event loop
        if self._use_lightrag and self.lightrag:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self.lightrag.add(text, metadata))
                else:
                    loop.run_until_complete(self.lightrag.add(text, metadata))
            except Exception as e:
                logger.warning(f"LightRAG add failed (non-fatal): {e}")

    def add_batch(self, texts: list[str], metadatas: list[dict]) -> None:
        """Batch add — works for both FAISS and Qdrant."""
        self.vector.add_batch(texts, metadatas)
        self.bm25.add_batch(texts, metadatas)
        if self._use_lightrag and self.lightrag:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self.lightrag.add_batch(texts))
                else:
                    loop.run_until_complete(self.lightrag.add_batch(texts))
            except Exception as e:
                logger.warning(f"LightRAG batch add failed (non-fatal): {e}")

    async def query_async(
        self,
        query: str,
        faiss_k: int = FAISS_TOP_K,
        lightrag_k: int = LIGHTRAG_TOP_K,
        payload_filter: dict | None = None,
    ) -> dict[str, list[dict]]:
        """Async parallel query of all stores."""
        vector_task = asyncio.get_event_loop().run_in_executor(
            None, lambda: self.vector.search(query, k=faiss_k, payload_filter=payload_filter)
        )
        bm25_task = asyncio.get_event_loop().run_in_executor(
            None, lambda: self.bm25.search(query, k=BM25_TOP_K)
        )
        lightrag_task = (
            self.lightrag.search(query, k=lightrag_k)
            if self._use_lightrag and self.lightrag
            else _empty_coroutine()
        )

        vector_results, bm25_results, lightrag_results = await asyncio.gather(
            vector_task, bm25_task, lightrag_task
        )
        if payload_filter:
            bm25_results = [r for r in bm25_results if r.get(payload_filter["field"]) == payload_filter["value"]]
        return {"faiss": vector_results, "bm25": bm25_results, "lightrag": lightrag_results}

    def query(self, query: str, k: int = FAISS_TOP_K) -> dict[str, list[dict]]:
        """Sync wrapper for query_async."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In Jupyter/Streamlit — use nest_asyncio or run directly
            import nest_asyncio
            nest_asyncio.apply()
        return loop.run_until_complete(self.query_async(query))

    def save(self) -> None:
        """Persist indexes to disk."""
        self.vector.save()
        self.bm25.save()
        logger.info(f"Saved vector index ({self.vector.count} vectors), BM25 ({self.bm25.count} docs)")
