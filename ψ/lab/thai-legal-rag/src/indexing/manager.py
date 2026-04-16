"""
IndexManager — unified interface for adding and querying stores.
Qdrant vector store + BM25 keyword search.
"""
from __future__ import annotations

import asyncio
import logging

from src.indexing.bm25_store import BM25Store
from src.indexing.qdrant_store import QdrantStore
from src.config import VECTOR_TOP_K, BM25_TOP_K

logger = logging.getLogger(__name__)


class IndexManager:
    def __init__(self):
        self.vector = QdrantStore()
        self.bm25 = BM25Store()

    def add(self, text: str, metadata: dict) -> None:
        self.vector.add(text, metadata)

    def add_batch(self, texts: list[str], metadatas: list[dict]) -> None:
        self.vector.add_batch(texts, metadatas)
        self.bm25.add_batch(texts, metadatas)

    async def query_async(
        self,
        query: str,
        vector_k: int = VECTOR_TOP_K,
        payload_filter: dict | None = None,
    ) -> dict[str, list[dict]]:
        """Async parallel query of all stores."""
        vector_task = asyncio.get_event_loop().run_in_executor(
            None, lambda: self.vector.search(query, k=vector_k, payload_filter=payload_filter)
        )
        bm25_task = asyncio.get_event_loop().run_in_executor(
            None, lambda: self.bm25.search(query, k=BM25_TOP_K)
        )

        vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
        if payload_filter:
            bm25_results = [r for r in bm25_results if r.get(payload_filter["field"]) == payload_filter["value"]]
        return {"vector": vector_results, "bm25": bm25_results}

    def query(self, query: str, k: int = VECTOR_TOP_K) -> dict[str, list[dict]]:
        """Sync wrapper for query_async."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        return loop.run_until_complete(self.query_async(query))

    def save(self) -> None:
        """Persist indexes to disk."""
        self.vector.save()
        self.bm25.save()
        logger.info(f"Saved vector index ({self.vector.count} vectors), BM25 ({self.bm25.count} docs)")
