---
title: ## LightRAG v1.3.1 Gotchas
tags: [lightrag, ocr, cache, python, dependencies]
created: 2026-04-14
source: Thai Legal RAG re-OCR + LightRAG indexing 2026-02-13
---

# ## LightRAG v1.3.1 Gotchas

## LightRAG v1.3.1 Gotchas

1. **OCR Cache Key Format**: `sha256(file_id).hexdigest()[:16] + ".json"` — note the `[:16]` truncation. Use `_cache_path(file_id)` from `src/ingestion/ocr.py` directly.

2. **history_messages KeyError bug**: `del pipeline_status["history_messages"][:]` fails on first run when dict is empty. Patch: initialize key first if not present.

3. **Removed imports in v1.3.1**: `from lightrag.llm import gpt_4o_mini_complete` — removed. Delete this import if using custom LLM function.

4. **Extra dependencies**: Must install `tiktoken` and `pipmaster` separately — not bundled with `lightrag-hku`.

5. **Indexing performance**: ~3-4 min/file. 24 files ≈ 80 min. Output: .graphml + vdb JSON (~87MB). Resumable — skips already-indexed docs via kv_store_doc_status.

---
*Added via Oracle Learn*
