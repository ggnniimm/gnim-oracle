# Lesson: Thai Legal RAG — FAISS Index Misalignment

**Date**: 2026-02-24
**Source**: faiss-misalignment-fix session

## Pattern 1: FAISS Misalignment After Metadata-Only Cleanup

When you delete entries from `metadata.pkl` by filtering (without touching FAISS), and then add new chunks afterward, the alignment is **permanently broken** for all subsequent chunks:

```
Before cleanup:
  FAISS[0..N]  ↔  metadata[0..N]  ✓ aligned

After filtering 375 entries from metadata only:
  FAISS[0..N]  (unchanged — 375 orphan vectors embedded)
  metadata[0..N-375]  (filtered)
  → misaligned from position (N-375) onward

After adding new chunks:
  FAISS[0..N] [N+1..N+374]  (new vectors appended at end)
  metadata[0..N-375] [N-374..N-1]  (new entries appended at end)
  → FAISS[N-374] ≠ metadata[N-374]  BROKEN
```

**Fix**: Always run `rebuild_faiss_index.py` after any metadata-only cleanup:
```bash
THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/rebuild_faiss_index.py
```

**Detection**: On startup, `faiss_store._load()` should check:
```python
if self._index.ntotal != len(self._metadata):
    logger.warning(f"FAISS misalignment: {self._index.ntotal} vectors vs {len(self._metadata)} metadata")
```

## Pattern 2: Orphan Vector Guard

When FAISS index has more vectors than metadata entries (orphan vectors), guard against IndexError:

```python
# In faiss_store.search():
for score, idx in zip(scores[0], indices[0]):
    if idx == -1:
        continue
    if idx >= len(self._metadata):  # orphan vector
        continue
    item = dict(self._index_meta(idx))
```

## Pattern 3: Source Injection in Reranker

**Problem**: Title chunk of a document ranks #1 (semantically close to query), but content chunks rank low (different vocabulary). LLM gets title only, not the answer.

**Pattern**: Thai legal หนังสือเวียน — title "เรื่อง ระยะเวลาในการตรวจรับพัสดุ" matches query, but content "งานจัดซื้อจัดจ้างที่มิใช่งานจ้างก่อสร้าง ภายใน ๕ วันทำการ" does not.

**Fix**: Source injection in `reranker.rerank()`:
```python
# After computing top-K, inject more chunks from rank-1 source
if top:
    top_source = top[0].get("source_name") or top[0].get("filename", "")
    top_source_count = sum(1 for item in top
        if (item.get("source_name") or item.get("filename", "")) == top_source)
    if top_source_count == 1 and top_source:
        extras = [item for item in deduped[top_k:]
                  if (item.get("source_name") or item.get("filename", "")) == top_source][:3]
        if extras:
            top = top + extras
```

## Pattern 4: Retrieval Tuning Parameters (2026-02-24 baseline)

```python
FAISS_TOP_K = 40      # capture deep content chunks (rank 29-31 for this query)
BM25_TOP_K = 20       # wider keyword recall
BM25_WEIGHT = 0.9     # keyword matches nearly equal to semantic
RERANK_TOP_K = 15     # more context to LLM
```

**Trade-off**: BM25_WEIGHT=0.9 makes false positives score higher. Monitor if diverse queries regress.

## Pattern 5: Rebuild Script

`pipeline/rebuild_faiss_index.py` — re-embeds all chunks from metadata.pkl and saves fresh FAISS index. Use after:
- Metadata-only cleanup (removing entries without rebuilding FAISS)
- Any in-place metadata patch that doesn't touch FAISS

Runtime: ~45 min for 14,637 chunks at batch_size=100.
