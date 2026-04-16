---
title: ## BM25 Rebuild Append Trap
tags: [bm25, index, rebuild, append-trap, persistence]
created: 2026-04-14
source: Thai Legal RAG BM25 rebuild fix 2026-02-25
---

# ## BM25 Rebuild Append Trap

## BM25 Rebuild Append Trap

Any search store that loads existing data in `__init__` will APPEND rather than REPLACE when you call a rebuild script. The store accumulates: 32k → 64k → 96k per run.

```python
class BM25Store:
    def __init__(self):
        self._load()  # loads existing file into self._corpus
    def add_batch(self, texts, metas):
        self._corpus.extend(...)  # appends to loaded data — TRAP
```

**Fix**: Wipe the index file before creating the store in rebuild scripts:
```python
if _BM25_FILE.exists():
    _BM25_FILE.unlink()
store = BM25Store()  # now starts fresh
```

**Invariant check**: After any index rebuild, `count(rebuilt_index) == count(source_data)`. If count is 2× source → append trap. If less → truncation or batch error.

Same pattern applies to any persistent store: FAISS, vector DBs, etc.

---
*Added via Oracle Learn*
