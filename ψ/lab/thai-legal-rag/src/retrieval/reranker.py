"""
Result fusion and reranking.
Merges FAISS + LightRAG results, deduplicates, returns top-K.
"""
from __future__ import annotations

import logging

from src.config import RERANK_TOP_K

logger = logging.getLogger(__name__)

# Weight for each source when combining scores
_SOURCE_WEIGHTS = {
    "faiss": 1.0,
    "lightrag": 0.9,  # slightly lower — graph responses are broader
    "bm25": 0.7,      # keyword match supplements semantic
}


def rerank(results: dict[str, list[dict]], top_k: int = RERANK_TOP_K) -> list[dict]:
    """
    Fuse FAISS + LightRAG results:
    1. Normalize scores within each source to [0, 1]
    2. Apply source weight
    3. Deduplicate by text similarity (first 200 chars)
    4. Sort by weighted score, return top_k
    """
    all_items: list[dict] = []

    for source, items in results.items():
        if not items:
            continue
        weight = _SOURCE_WEIGHTS.get(source, 1.0)

        # Normalize scores within this source
        max_score = max(item.get("score", 0) for item in items) or 1.0
        for item in items:
            norm_score = item.get("score", 0) / max_score
            item = dict(item)  # copy
            item["weighted_score"] = norm_score * weight
            all_items.append(item)

    # Deduplicate by text prefix
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in sorted(all_items, key=lambda x: x["weighted_score"], reverse=True):
        text_key = item.get("text", "")[:200].strip()
        if text_key not in seen:
            seen.add(text_key)
            deduped.append(item)
        if len(deduped) >= top_k * 5:
            break  # Early exit after collecting enough candidates

    top = deduped[:top_k]

    # Source injection: if rank-1 source appears only once in top-K,
    # its title chunk ranked high but content chunks didn't.
    # Inject up to 3 more chunks from the same source from the candidate pool.
    if top:
        top_source = top[0].get("source_name") or top[0].get("filename", "")
        top_source_count = sum(
            1 for item in top
            if (item.get("source_name") or item.get("filename", "")) == top_source
        )
        if top_source_count == 1 and top_source:
            extras = [
                item for item in deduped[top_k:]
                if (item.get("source_name") or item.get("filename", "")) == top_source
            ][:3]
            if extras:
                top = top + extras
                logger.debug(f"Source injection: added {len(extras)} chunks from '{top_source}'")

    logger.debug(
        f"Reranked {len(all_items)} items → {len(deduped)} deduped → top {len(top)}"
    )
    return top
