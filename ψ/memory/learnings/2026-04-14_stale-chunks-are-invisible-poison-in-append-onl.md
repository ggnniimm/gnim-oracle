---
title: ## Stale Chunks Are Invisible Poison in Append-Only Indexes
tags: [rag, indexing, faiss, stale-data, debugging, thai-legal-rag]
created: 2026-04-14
source: Oracle Learn
---

# ## Stale Chunks Are Invisible Poison in Append-Only Indexes

## Stale Chunks Are Invisible Poison in Append-Only Indexes

### Context
Thai Legal RAG — TC-011 was failing intermittently. Root cause: stale FAISS chunks from before MD file edits.

### Pattern: Stale Chunk Contamination
When you edit source MD files, append-only indexing creates contradictory data. The old and new chunks both exist in the index simultaneously. The LLM gets confused by conflicting information from ghost chunks of the same document.

**Symptom**: LLM picks wrong answer even though correct chunks are visible in top-15 reranked results.

**Root Cause**: Old document version summarized "ผู้อำนวยการองค์การสะพานปลา", new version says "หัวหน้าหน่วยงานของรัฐ". Both chunks reach LLM. LLM picks wrong one.

### Fix
Full index rebuild (delete FAISS + BM25 + dedup.db, re-index from scratch) is the nuclear option but sometimes the only clean fix.

Add `--rebuild` flag to index script that deletes existing chunks for a file before re-indexing — prevents future accumulation.

### Pattern: Trace Full Pipeline Before Guessing
When retrieval seems correct (right docs found, right chunks in top-15) but LLM answers wrong, suspect data quality — not the reranker or prompt. Trace FAISS → BM25 → dedup → MMR → source completion → LLM context to find ghost data.

### Pattern: Non-Deterministic LLM Masks Retrieval Bugs
If a TC passes and fails intermittently, the root cause may be data contamination — not random LLM variance. Need retrieval-only eval mode that checks chunk content directly.

---
*Added via Oracle Learn*
