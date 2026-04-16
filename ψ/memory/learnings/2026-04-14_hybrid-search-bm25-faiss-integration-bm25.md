---
title: ## Hybrid Search — BM25 + FAISS Integration
tags: [bm25, faiss, hybrid-search, asyncio, thai-legal]
created: 2026-04-14
source: Thai Legal RAG BM25+FAISS implementation 2026-02-23
---

# ## Hybrid Search — BM25 + FAISS Integration

## Hybrid Search — BM25 + FAISS Integration

BM25 integrates into async retrieval pipeline via `asyncio.get_event_loop().run_in_executor()` — same pattern as FAISS. Both run in parallel under `asyncio.gather()`.

**Key details**:
- rank_bm25 has no incremental update — must rebuild BM25Okapi from full corpus on each add. At 12,370 docs ~1 second. Use `_dirty` flag to defer rebuild until next search.
- pythainlp newmm tokenizer works directly as BM25 tokenizer for Thai text.
- Score normalization: reranker normalizes per-source (divide by max_score), so BM25 raw scores are automatically brought to [0,1].
- Weight: bm25=0.7 (vs faiss=1.0) — keyword match supplements semantic, doesn't replace it.

**Pitfall — mutation in bootstrap**:
```python
# WRONG — mutates loaded data
texts = [d.pop("text") for d in meta]
# RIGHT — non-mutating
texts = [d["text"] for d in meta]
metas = [{k: v for k, v in d.items() if k != "text"} for d in meta]
```

Cross-source dedup in retriever uses `text[:100]` as key. Reranker does additional dedup on `text[:200]`.

---
*Added via Oracle Learn*
