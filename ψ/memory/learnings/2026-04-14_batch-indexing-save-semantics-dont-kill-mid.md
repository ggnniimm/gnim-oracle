---
title: ## Batch Indexing Save Semantics — Don't Kill Mid-Run
tags: [batch-indexing, faiss, dedup, save-semantics, interruption]
created: 2026-04-14
source: Thai Legal RAG re-index session 2026-02-24
---

# ## Batch Indexing Save Semantics — Don't Kill Mid-Run

## Batch Indexing Save Semantics — Don't Kill Mid-Run

Different storage layers in Thai Legal RAG batch indexing have different save timing:
- `dedup.db`: per-chunk (real-time) — survives kill
- `ocr_cache/`: per-file (real-time) — survives kill
- `faiss_index/`: end of process only — LOST if killed
- `bm25_index/`: end of process only — LOST if killed

**Consequence**: Killing mid-run leaves dedup.db with hashes for files not in FAISS. Next run skips those files (dedup says indexed) but FAISS won't have them → permanently missing vectors.

**Recovery**: Wipe dedup.db + FAISS + BM25, re-run from scratch. OCR cache survives.

**Progress monitoring**: Use dedup.db as real-time proxy when FAISS is unreadable mid-run:
```python
total = conn.execute('SELECT COUNT(*) FROM indexed_chunks').fetchone()[0]
new_chunks = total - baseline
```

---
*Added via Oracle Learn*
