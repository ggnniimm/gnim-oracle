# Stale Chunks in Append-Only Indexing

**Date**: 2026-03-01
**Source**: thai-legal-rag TC-011 debugging
**Tags**: faiss, indexing, retrieval, stale-data, debugging

## Pattern

When using append-only indexing (dedup by content hash, never delete):
- Editing source MD files creates NEW chunks with updated text
- OLD chunks with previous text remain in the index
- Both old and new versions get retrieved simultaneously
- LLM receives contradictory information and may pick the wrong version

## Symptoms

- Retrieval looks correct (right document found, right chunks in FAISS top-40)
- Reranking looks correct (answer chunks in top-15)
- But LLM answer is wrong or inconsistent
- Non-deterministic pass/fail on eval

## Root Cause

`index_md_folder.py` uses `is_indexed(text)` to skip duplicates, but when you edit a file:
1. Old chunk text != new chunk text → both get indexed
2. Old chunk says "ผู้อำนวยการองค์การสะพานปลา" (specific case)
3. New chunk says "หัวหน้าหน่วยงานของรัฐ" (correct general answer)
4. LLM sees both, gets confused

## Fix

**Nuclear option (used)**: Delete FAISS index + BM25 index + dedup.db, rebuild from scratch.
- 971 files, ~20 minutes, 21,823 chunks
- Backup old index files first (`.bak_pre_rebuild`)

**Better long-term fix (TODO)**: Add `--rebuild` flag that removes existing chunks for a source before re-indexing.

## Key Insight

Trace the FULL pipeline before guessing at fixes. The bug was in the data, not the algorithm.
