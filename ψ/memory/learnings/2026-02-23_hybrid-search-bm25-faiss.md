# Lesson: Hybrid Search — BM25 + FAISS Integration

**Date**: 2026-02-23
**Source**: thai-legal-rag implementation session

## Pattern

BM25 integrates into an async retrieval pipeline via `asyncio.get_event_loop().run_in_executor()` — the same pattern used for FAISS (also synchronous). Both run truly in parallel under `asyncio.gather()`. LightRAG (native async) gets its own coroutine slot.

```python
bm25_task = asyncio.get_event_loop().run_in_executor(
    None, lambda: self.bm25.search(query, k=BM25_TOP_K)
)
faiss_results, bm25_results, lightrag_results = await asyncio.gather(
    faiss_task, bm25_task, lightrag_task
)
```

## Key Details

- **rank_bm25 has no incremental update** — must rebuild BM25Okapi from full corpus on each add. At 12,370 docs this takes ~1 second. Use `_dirty` flag to defer rebuild until next search.
- **pythainlp newmm** tokenizer works directly as BM25 tokenizer for Thai text — no additional preprocessing.
- **Score normalization**: reranker already normalizes per-source (divide by max_score), so BM25 raw scores (unbounded) are automatically brought to [0,1].
- **Weight**: bm25=0.7 (vs faiss=1.0, lightrag=0.9) — keyword match supplements semantic, doesn't replace it.

## Pitfall: Mutation in Bootstrap

`d.pop("text")` in a bootstrap loop mutates the loaded metadata list, leaving empty "text" keys. Use `d["text"]` instead:

```python
# WRONG — mutates loaded data
texts = [d.pop("text") for d in meta]

# RIGHT — non-mutating
texts = [d["text"] for d in meta]
metas = [{k: v for k, v in d.items() if k != "text"} for d in meta]
```

## Architecture Result

```
query → FAISS (semantic) + BM25 (lexical) + LightRAG (graph) → rerank → answer
```

Cross-source dedup in retriever uses text[:100] as key. Reranker does additional dedup on text[:200]. Both paths cover the case where FAISS and BM25 return the same chunk.
