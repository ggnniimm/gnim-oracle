---
title: ## Chunk Boundary + Dedup Pool: Hidden Retrieval Ceilings
tags: [rag, retrieval, faiss, chunk-engineering, embeddings, thai-legal-rag]
created: 2026-04-14
source: Oracle Learn
---

# ## Chunk Boundary + Dedup Pool: Hidden Retrieval Ceilings

## Chunk Boundary + Dedup Pool: Hidden Retrieval Ceilings

### Context
Thai Legal RAG — TC-042 debugging: critical phrase "ไม่ต้องรอกระบวนการพิจารณาผู้ทิ้งงาน" never reached LLM.

### Pattern: Dedup Pool is a Hard Ceiling
`RERANK_TOP_K * 5 = 75` is the maximum candidates for MMR reranking. If your critical chunk is at FAISS rank 76+, it's invisible — no amount of source completion or prompt tuning helps. This parameter silently determines what knowledge can reach the LLM.

**Fix**: Increase dedup pool to `top_k * 8` or higher.

### Pattern: Cross-Referencing Beats Chunk Optimization
When a document can't rank high enough for a query, put the critical fact in a document that does rank #1. Cross-referencing the knowledge into a consistently top-ranked doc is more reliable than trying to push a poorly-ranked doc higher.

### Pattern: Shortened Text Can Rank Worse
FAISS cosine similarity rewards matching vocabulary. Concise arrow notation (→) loses semantic overlap with query terms compared to verbose Thai prose. Shortening bullets to fit within CHUNK_SIZE may actually push the chunk further down in FAISS rankings.

### Pattern: Verify Index File Paths Before Deletion
`data/faiss_index.bin` ≠ `data/faiss_index/index.faiss`
`data/bm25_index.pkl` ≠ `data/bm25_index/bm25.pkl`
`rm -f` silently succeeds on missing files — wrong paths mean "clean rebuild" is actually appending to old corrupted index. Always verify paths with ls before deleting.

### Pattern: Low-Cardinality Metadata Hurts Embedding Quality
Gemini embedding model treats bracket-prefix text as high-weight context. Adding metadata that 95% of documents share (topic = "การจัดซื้อจัดจ้าง") dilutes the embedding signal. Original minimal prefix `[ref_number | date | category]` outperforms enriched prefixes because each field has genuine discriminative power.

---
*Added via Oracle Learn*
