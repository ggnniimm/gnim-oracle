---
title: ## Stale Chunks in Append-Only Indexing
tags: [faiss, indexing, stale-chunks, dedup, append-only]
created: 2026-04-14
source: Thai Legal RAG TC-011 debugging 2026-03-01
---

# ## Stale Chunks in Append-Only Indexing

## Stale Chunks in Append-Only Indexing

When using append-only indexing (dedup by content hash), editing source MD files creates NEW chunks with updated text while OLD chunks with previous text remain. Both get retrieved simultaneously — LLM receives contradictory information.

**Symptoms**: Retrieval looks correct, reranking looks correct, but LLM answer is wrong or inconsistent. Non-deterministic pass/fail on eval.

**Root cause**: `index_md_folder.py` uses `is_indexed(text)` to skip duplicates. Edited text → both old and new get indexed → LLM sees both versions.

**Fix (nuclear option)**: Delete FAISS index + BM25 index + dedup.db, rebuild from scratch. Backup first.

**Long-term fix (TODO)**: Add `--rebuild` flag that removes existing chunks for a source before re-indexing.

**Key insight**: Trace the FULL pipeline before guessing at fixes. The bug was in the data, not the algorithm.

---
*Added via Oracle Learn*
