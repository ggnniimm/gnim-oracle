"""
IndexManager — unified interface for adding and querying both stores.
FAISS + LightRAG are implementation details; callers use this class.
"""
from __future__ import annotations

import asyncio
import logging

from src.indexing.faiss_store import FAISSStore
from src.indexing.lightrag_store import LightRAGStore
from src.config import FAISS_TOP_K, LIGHTRAG_TOP_K

logger = logging.getLogger(__name__)


class IndexManager:
    def __init__(self, use_lightrag: bool = True):
        self.faiss = FAISSStore()
        self.lightrag = LightRAGStore() if use_lightrag else None
        self._use_lightrag = use_lightrag

    def add(self, text: str, metadata: dict) -> None:
        """
        Add a single chunk to both indexes.
        Runs LightRAG in async event loop.
        """
        # FAISS is sync
        self.faiss.add(text, metadata)

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
        """Batch add — more efficient for FAISS."""
        self.faiss.add_batch(texts, metadatas)
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
    ) -> dict[str, list[dict]]:
        """Async parallel query of both stores."""
        faiss_task = asyncio.get_event_loop().run_in_executor(
            None, lambda: self.faiss.search(query, k=faiss_k)
        )
        lightrag_task = (
            self.lightrag.search(query, k=lightrag_k)
            if self._use_lightrag and self.lightrag
            else asyncio.coroutine(lambda: [])()
        )

        faiss_results, lightrag_results = await asyncio.gather(
            faiss_task, lightrag_task
        )
        return {"faiss": faiss_results, "lightrag": lightrag_results}

    def query(self, query: str, k: int = FAISS_TOP_K) -> dict[str, list[dict]]:
        """Sync wrapper for query_async."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In Jupyter/Streamlit — use nest_asyncio or run directly
            import nest_asyncio
            nest_asyncio.apply()
        return loop.run_until_complete(self.query_async(query))

    def save(self) -> None:
        """Persist FAISS index to disk."""
        self.faiss.save()
        logger.info(f"Saved FAISS index ({self.faiss.count} vectors)")
