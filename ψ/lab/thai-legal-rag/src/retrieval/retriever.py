"""
Parallel retriever — queries Qdrant vector store and BM25 simultaneously.
"""
from __future__ import annotations

import asyncio
import logging
import re

from src.indexing.manager import IndexManager
from src.retrieval.glossary import glossary_expand, vocab_expand
from src.retrieval.query_expand import expand_query, is_specific_query
from src.config import VECTOR_TOP_K, ORIGINAL_QUERY_BOOST

logger = logging.getLogger(__name__)

_JUDGMENT_KEYWORDS = re.compile(r"คำพิพากษา|คำสั่งศาล|ศาลปกครอง|คดีปกครอง")
_ATTORNEY_KEYWORDS = re.compile(r"อัยการสูงสุด|สำนักงานอัยการ|คำวินิจฉัยอัยการ|อัยการ(?:สูงสุด|จังหวัด|พิเศษ)")

# Statute carve-out: when a "specific" query targets a statutory provision
# (มาตรา/ข้อ/หมวด/วรรค/ม.X), BM25 alone buries the statute chunk under
# doc-ID/material-code noise. Run an additional vector search filtered to
# the statute file_ids so the section text surfaces.
_STATUTE_PROVISION_PATTERN = re.compile(
    r"มาตรา\s*[\d๐-๙]+|ข้อ\s*[\d๐-๙]+|หมวด\s*[\d๐-๙]+"
    r"|วรรค\s*(?:หนึ่ง|สอง|สาม|สี่|ห้า|\d+)"
    r"|ม\.\s*\d+"
)
STATUTE_FILE_IDS = [
    "1raRAyQai8gybh1jaHaoHCSF-E797gISF",  # พ.ร.บ.จัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ 2560
    "1bGmZda4_AEDx8jc4VWsnq15hQWpA66IV",  # ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างฯ 2560
]
_STATUTE_VECTOR_K = 10


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
        vector_k: int = VECTOR_TOP_K,
        history: list[dict] | None = None,
    ) -> dict[str, list[dict]]:
        payload_filter = _detect_payload_filter(query, history)
        """
        Async retrieval with optional query expansion.
        Returns {"vector": [...], "bm25": [...]}.
        """
        specific = is_specific_query(query)
        if expand and not specific:
            queries = expand_query(query)
            # Also append vocabulary-synonym expansions (covers spelling variants
            # Gemini may miss, e.g. ลงนาม↔ลงลายมือชื่อ, e-GP↔e - GP).
            # Uses vocab_expand (not full glossary) to avoid semantic-expansion
            # regressions from entries like ขยายเวลา/บอกเลิกสัญญา.
            vocab = vocab_expand(query)
            if vocab:
                queries = list(dict.fromkeys(queries + vocab[:3]))
            logger.debug(f"Expanded to {len(queries)} queries (with vocab synonyms)")
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
            return await self.index.query_async(q, vector_k=vector_k, payload_filter=payload_filter)

        all_results = await asyncio.gather(*[_query_one(q) for q in queries])

        # Merge: deduplicate by text content.
        # Boost scores from the original query (index 0) so it dominates
        # over noise from expanded queries after reranker normalization.
        merged_vector: dict[str, dict] = {}
        merged_bm25: dict[str, dict] = {}

        for qi, result_set in enumerate(all_results):
            boost = ORIGINAL_QUERY_BOOST if qi == 0 else 1.0
            for item in result_set.get("vector", []):
                item = dict(item)
                item["score"] = item.get("score", 0) * boost
                key = item.get("text", "")[:100]
                if key not in merged_vector or item["score"] > merged_vector[key]["score"]:
                    merged_vector[key] = item
            for item in result_set.get("bm25", []):
                item = dict(item)
                item["score"] = item.get("score", 0) * boost
                key = item.get("text", "")[:100]
                if key not in merged_bm25 or item["score"] > merged_bm25[key]["score"]:
                    merged_bm25[key] = item

        if specific:
            # Statute carve-out: for มาตรา/ข้อ/หมวด/วรรค/ม.X queries, BM25 alone
            # buries the statute chunk under doc-ID/material-code noise (e.g.
            # "ม. 103 รื้อกอง" in material-code circulars outranks มาตรา ๑๐๓).
            # Run an additional vector search filtered to statute file_ids so
            # the section text surfaces.
            if _STATUTE_PROVISION_PATTERN.search(query):
                logger.debug(f"Statute carve-out: filtered vector search on statute file_ids")
                loop = asyncio.get_event_loop()
                statute_hits = await loop.run_in_executor(
                    None,
                    lambda: self.index.vector.search(
                        query,
                        k=_STATUTE_VECTOR_K,
                        payload_filter={"field": "file_id", "values": STATUTE_FILE_IDS},
                    ),
                )
                return {"vector": statute_hits, "bm25": list(merged_bm25.values())}
            # Doc-ID lookup (bare 4+ digit): BM25 exact match is authoritative.
            # Vector embeddings of bare numbers return generic semantic matches that add noise.
            logger.debug(f"Specific query — returning BM25 only (skipping vector)")
            return {"vector": [], "bm25": list(merged_bm25.values())}

        return {
            "vector": list(merged_vector.values()),
            "bm25": list(merged_bm25.values()),
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
