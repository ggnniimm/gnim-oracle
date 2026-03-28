"""
Parallel retriever — queries FAISS and LightRAG simultaneously.
"""
from __future__ import annotations

import asyncio
import logging
import re

from src.indexing.manager import IndexManager
from src.retrieval.glossary import glossary_expand
from src.retrieval.query_expand import expand_query, is_specific_query
from src.config import FAISS_TOP_K, LIGHTRAG_TOP_K, ORIGINAL_QUERY_BOOST

logger = logging.getLogger(__name__)

_JUDGMENT_KEYWORDS = re.compile(r"คำพิพากษา|คำสั่งศาล|ศาลปกครอง|คดีปกครอง")
_ATTORNEY_KEYWORDS = re.compile(r"อัยการสูงสุด|สำนักงานอัยการ|คำวินิจฉัยอัยการ|อัยการ(?:สูงสุด|จังหวัด|พิเศษ)")


def _detect_payload_filter(query: str, history: list[dict] | None = None) -> dict | None:
    """Return {field, value} payload filter if query targets a specific source type."""
    def _check(q: str) -> dict | None:
        if _JUDGMENT_KEYWORDS.search(q):
            return {"field": "category", "value": "คำพิพากษา"}
        if _ATTORNEY_KEYWORDS.search(q):
            return {"field": "issued_by", "value": "สำนักงานอัยการสูงสุด"}
        return None

    result = _check(query)
    if result:
        return result
    if history:
        for msg in history[-6:]:
            if msg.get("role") == "user":
                result = _check(msg.get("content", ""))
                if result:
                    return result
    return None


class Retriever:
    def __init__(self, index_manager: IndexManager):
        self.index = index_manager

    async def retrieve_async(
        self,
        query: str,
        expand: bool = True,
        faiss_k: int = FAISS_TOP_K,
        lightrag_k: int = LIGHTRAG_TOP_K,
        history: list[dict] | None = None,
    ) -> dict[str, list[dict]]:
        payload_filter = _detect_payload_filter(query, history)
        """
        Async retrieval with optional query expansion.
        Returns {"faiss": [...], "lightrag": [...]}.
        """
        specific = is_specific_query(query)
        if expand and not specific:
            queries = expand_query(query)
            logger.debug(f"Expanded to {len(queries)} queries")
        else:
            if expand and specific:
                gloss = glossary_expand(query)
                if gloss:
                    queries = [query] + gloss[:3]
                    logger.debug(f"Specific query — glossary only: {queries}")
                else:
                    queries = [query]
                    logger.debug(f"Skipping expansion — specific query, no glossary match: {query!r}")
            else:
                queries = [query]

        # Run all queries in parallel, collect all results
        async def _query_one(q: str) -> dict[str, list[dict]]:
            return await self.index.query_async(q, faiss_k=faiss_k, lightrag_k=lightrag_k, payload_filter=payload_filter)

        all_results = await asyncio.gather(*[_query_one(q) for q in queries])

        # Merge: deduplicate by text content.
        # Boost scores from the original query (index 0) so it dominates
        # over noise from expanded queries after reranker normalization.
        merged_faiss: dict[str, dict] = {}
        merged_bm25: dict[str, dict] = {}
        merged_lightrag: dict[str, dict] = {}

        for qi, result_set in enumerate(all_results):
            boost = ORIGINAL_QUERY_BOOST if qi == 0 else 1.0
            for item in result_set.get("faiss", []):
                item = dict(item)
                item["score"] = item.get("score", 0) * boost
                key = item.get("text", "")[:100]
                if key not in merged_faiss or item["score"] > merged_faiss[key]["score"]:
                    merged_faiss[key] = item
            for item in result_set.get("bm25", []):
                item = dict(item)
                item["score"] = item.get("score", 0) * boost
                key = item.get("text", "")[:100]
                if key not in merged_bm25 or item["score"] > merged_bm25[key]["score"]:
                    merged_bm25[key] = item
            for item in result_set.get("lightrag", []):
                item = dict(item)
                item["score"] = item.get("score", 0) * boost
                key = item.get("text", "")[:100]
                if key not in merged_lightrag or item["score"] > merged_lightrag[key]["score"]:
                    merged_lightrag[key] = item

        if specific:
            # For ID/provision lookups, BM25 exact match is authoritative.
            # FAISS embeddings of bare numbers return generic semantic matches that add noise.
            logger.debug(f"Specific query — returning BM25 only (skipping FAISS)")
            return {"faiss": [], "bm25": list(merged_bm25.values()), "lightrag": []}

        return {
            "faiss": list(merged_faiss.values()),
            "bm25": list(merged_bm25.values()),
            "lightrag": list(merged_lightrag.values()),
        }

    def retrieve(self, query: str, expand: bool = True, history: list[dict] | None = None) -> dict[str, list[dict]]:
        """Sync wrapper."""
        try:
            loop = asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(self.retrieve_async(query, expand=expand, history=history))
        except RuntimeError:
            return asyncio.run(self.retrieve_async(query, expand=expand, history=history))
