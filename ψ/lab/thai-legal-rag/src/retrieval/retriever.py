"""
Parallel retriever — queries FAISS and LightRAG simultaneously.
"""
from __future__ import annotations

import asyncio
import logging

from src.indexing.manager import IndexManager
from src.retrieval.query_expand import expand_query
from src.config import FAISS_TOP_K, LIGHTRAG_TOP_K

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self, index_manager: IndexManager):
        self.index = index_manager

    async def retrieve_async(
        self,
        query: str,
        expand: bool = True,
        faiss_k: int = FAISS_TOP_K,
        lightrag_k: int = LIGHTRAG_TOP_K,
    ) -> dict[str, list[dict]]:
        """
        Async retrieval with optional query expansion.
        Returns {"faiss": [...], "lightrag": [...]}.
        """
        if expand:
            queries = expand_query(query)
            logger.debug(f"Expanded to {len(queries)} queries")
        else:
            queries = [query]

        # Run all queries in parallel, collect all results
        async def _query_one(q: str) -> dict[str, list[dict]]:
            return await self.index.query_async(q, faiss_k=faiss_k, lightrag_k=lightrag_k)

        all_results = await asyncio.gather(*[_query_one(q) for q in queries])

        # Merge: deduplicate by text content
        merged_faiss: dict[str, dict] = {}
        merged_lightrag: dict[str, dict] = {}

        for result_set in all_results:
            for item in result_set.get("faiss", []):
                key = item.get("text", "")[:100]
                if key not in merged_faiss or item["score"] > merged_faiss[key]["score"]:
                    merged_faiss[key] = item
            for item in result_set.get("lightrag", []):
                key = item.get("text", "")[:100]
                if key not in merged_lightrag or item["score"] > merged_lightrag[key]["score"]:
                    merged_lightrag[key] = item

        return {
            "faiss": list(merged_faiss.values()),
            "lightrag": list(merged_lightrag.values()),
        }

    def retrieve(self, query: str, expand: bool = True) -> dict[str, list[dict]]:
        """Sync wrapper."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        return loop.run_until_complete(self.retrieve_async(query, expand=expand))
