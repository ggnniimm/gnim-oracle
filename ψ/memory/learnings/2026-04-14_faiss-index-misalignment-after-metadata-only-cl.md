---
title: ## FAISS Index Misalignment After Metadata-Only Cleanup
tags: [faiss, misalignment, metadata, reranker, thai-legal]
created: 2026-04-14
source: FAISS misalignment fix session 2026-02-24
---

# ## FAISS Index Misalignment After Metadata-Only Cleanup

## FAISS Index Misalignment After Metadata-Only Cleanup

When you delete entries from metadata.pkl by filtering (without touching FAISS), then add new chunks afterward, alignment is permanently broken for all subsequent chunks. FAISS[i] ≠ metadata[i] after the deletion point.

**Fix**: Always run `rebuild_faiss_index.py` after any metadata-only cleanup.

**Detection**: Check on startup: `if self._index.ntotal != len(self._metadata): logger.warning(...)`

**Orphan vector guard** (when FAISS has more vectors than metadata):
```python
if idx >= len(self._metadata):  # orphan vector
    continue
```

**Source injection in reranker**: When title chunk ranks #1 but content chunks rank low (different vocabulary), inject more chunks from rank-1 source after computing top-K. Thai legal หนังสือเวียน: title matches query semantically but answer is in content.

**Baseline tuning parameters** (2026-02-24): FAISS_TOP_K=40, BM25_TOP_K=20, BM25_WEIGHT=0.9, RERANK_TOP_K=15. BM25_WEIGHT=0.9 makes false positives score higher — monitor for regressions.

---
*Added via Oracle Learn*
