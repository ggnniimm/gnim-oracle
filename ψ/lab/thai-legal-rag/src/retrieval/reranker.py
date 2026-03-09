"""
Result fusion and reranking with MMR (Maximal Marginal Relevance).

Pipeline:
1. Normalize scores within each source to [0, 1]
2. Apply source weight
3. Deduplicate by exact text prefix
4. MMR selection — balance relevance vs diversity
5. Source completion — inject extra chunks from sources already in top-K
"""
from __future__ import annotations

import logging

from pythainlp.tokenize import word_tokenize

from src.config import BM25_WEIGHT, MMR_INJECT_EXTRAS, MMR_LAMBDA, RERANK_TOP_K, RECENCY_BOOST

logger = logging.getLogger(__name__)

_SOURCE_WEIGHTS = {
    "faiss": 1.0,
    "lightrag": 0.9,
    "bm25": BM25_WEIGHT,
}


def _jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two Thai texts."""
    a_tok = set(word_tokenize(a[:400], keep_whitespace=False))
    b_tok = set(word_tokenize(b[:400], keep_whitespace=False))
    if not a_tok or not b_tok:
        return 0.0
    inter = len(a_tok & b_tok)
    union = len(a_tok | b_tok)
    return inter / union if union else 0.0


def _mmr_select(candidates: list[dict], top_k: int, lambda_: float) -> list[dict]:
    """
    Iterative MMR selection from candidates.
    Each step picks the item maximising:
        lambda * relevance_score  -  (1 - lambda) * max_similarity_to_selected
    """
    selected: list[dict] = []
    remaining = list(candidates)

    while len(selected) < top_k and remaining:
        if not selected:
            best = max(remaining, key=lambda x: x["weighted_score"])
        else:
            sel_texts = [s.get("text", "") for s in selected]

            def _score(x: dict) -> float:
                rel = x["weighted_score"]
                div = max(_jaccard(x.get("text", ""), t) for t in sel_texts)
                return lambda_ * rel - (1 - lambda_) * div

            best = max(remaining, key=_score)

        selected.append(best)
        remaining.remove(best)

    return selected


def rerank(
    results: dict[str, list[dict]],
    top_k: int = RERANK_TOP_K,
    query: str = "",
) -> list[dict]:
    """
    Fuse FAISS + BM25 + LightRAG results, deduplicate, MMR-select, source-complete.
    query: original query string, used for glossary-based injection from dedup pool.
    """
    all_items: list[dict] = []

    for source, items in results.items():
        if not items:
            continue
        weight = _SOURCE_WEIGHTS.get(source, 1.0)
        max_score = max(item.get("score", 0) for item in items) or 1.0
        for item in items:
            norm_score = item.get("score", 0) / max_score
            item = dict(item)
            item["weighted_score"] = norm_score * weight
            # Recency boost: newer documents get a small score bump
            date_str = item.get("date", "")
            if date_str and RECENCY_BOOST > 0:
                try:
                    year = int(date_str[:4])
                    age_factor = max(0.0, min(1.0, (year - 2020) / 6))
                    item["weighted_score"] *= (1.0 + RECENCY_BOOST * age_factor)
                except (ValueError, IndexError):
                    pass
            all_items.append(item)

    # Exact-text dedup — keep best score per unique text
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in sorted(all_items, key=lambda x: x["weighted_score"], reverse=True):
        key = item.get("text", "")[:200].strip()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
        if len(deduped) >= top_k * 8:
            break

    # MMR selection
    top = _mmr_select(deduped, top_k, MMR_LAMBDA)

    # Source completion — for every source already in top, inject up to
    # MMR_INJECT_EXTRAS more chunks from the candidate pool that didn't make it.
    # This ensures an "anchor" chunk pulling in a doc also brings its content.
    if MMR_INJECT_EXTRAS > 0:
        top_sources = {
            item.get("source_name") or item.get("filename", "")
            for item in top
            if item.get("source_name") or item.get("filename", "")
        }
        top_texts = {item.get("text", "")[:200].strip() for item in top}
        extras: list[dict] = []
        injected_per_source: dict[str, int] = {}

        for item in deduped[top_k:]:
            src = item.get("source_name") or item.get("filename", "")
            text_key = item.get("text", "")[:200].strip()
            if (
                src in top_sources
                and text_key not in top_texts
                and injected_per_source.get(src, 0) < MMR_INJECT_EXTRAS
            ):
                extras.append(item)
                top_texts.add(text_key)
                injected_per_source[src] = injected_per_source.get(src, 0) + 1

        if extras:
            logger.debug(
                f"Source completion: injected {len(extras)} chunks "
                f"from {len(injected_per_source)} sources"
            )
            top = top + extras

    # Glossary injection — if the query triggers glossary expansion terms,
    # scan remaining dedup pool for chunks containing those terms.
    # This rescues relevant documents that MMR diversity penalty excluded.
    # Runs BEFORE source expansion so injected sources also get expanded.
    if query:
        from src.retrieval.glossary import glossary_expand
        gloss_terms = glossary_expand(query)
        if gloss_terms:
            top_texts_gl = {item.get("text", "")[:200].strip() for item in top}
            top_sources_gl = {
                item.get("source_name") or item.get("filename", "")
                for item in top
            }
            gloss_extras: list[dict] = []
            max_gloss_inject = 3

            for item in deduped:
                if len(gloss_extras) >= max_gloss_inject:
                    break
                text_key = item.get("text", "")[:200].strip()
                if text_key in top_texts_gl:
                    continue
                src = item.get("source_name") or item.get("filename", "")
                if src in top_sources_gl:
                    continue  # already have chunks from this source
                text = item.get("text", "")
                # Check if chunk contains at least 2 glossary terms
                match_count = sum(1 for t in gloss_terms if t in text)
                if match_count >= 2:
                    gloss_extras.append(item)
                    top_texts_gl.add(text_key)

            if gloss_extras:
                for ge in gloss_extras:
                    ge["_gloss_injected"] = True
                logger.debug(
                    f"Glossary injection: {len(gloss_extras)} chunks "
                    f"matching glossary terms for query {query!r}"
                )
                top = top + gloss_extras

    logger.debug(
        f"Reranked {len(all_items)} items → {len(deduped)} deduped → top {len(top)}"
    )
    return top
