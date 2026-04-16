---
title: ## BM25 + FAISS Hybrid Search Integration (2026-02-23)
tags: [bm25, faiss, hybrid-search, asyncio, indexing, thai-legal-rag, rank-bm25]
created: 2026-04-14
source: retro: 2026-02-23 hybrid-search-bm25-faiss
---

# ## BM25 + FAISS Hybrid Search Integration (2026-02-23)

## BM25 + FAISS Hybrid Search Integration (2026-02-23)

**BM25 integrates cleanly into asyncio via run_in_executor**: Same pattern as FAISS. Both are synchronous, so both run via `run_in_executor`. LightRAG is the only async one — genuinely parallel execution with `asyncio.gather`.

**rank_bm25 doesn't support incremental update**: Must rebuild from full corpus each time. Fast at 12K docs (~1 second). Bootstrap script must NOT use `d.pop("text")` — use `d["text"]` to avoid mutating the loaded metadata in place.

**PyThaiNLP newmm tokenizer works directly for BM25**: No extra preprocessing needed for Thai text corpus tokenization.

**BM25 weight in reranker**: `"bm25": 0.7` weight — BM25 provides high-precision keyword matching that dense vectors miss (exact section numbers, legal terms with specific spelling).

**Short, surgical sessions work when plan is complete**: Ming arriving with a fully-formed plan meant pure translation from plan to code. 7 files touched, 2 created, index bootstrapped, smoke test passed in one session with no backtracking. Reading files in parallel before touching anything is the right starting instinct.

**Always prefer non-mutating dict access**: `d["text"]` not `d.pop("text")` when extracting fields from loaded data. pop() would silently corrupt all remaining entries.

**Complete verification covers all paths**: The smoke test verified search path but not the `add_batch` path (incremental indexing during ingestion). Don't declare done without testing both read and write paths.

---
*Added via Oracle Learn*
