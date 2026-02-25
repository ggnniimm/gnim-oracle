# BM25 Rebuild Append Trap

**Date**: 2026-02-25
**Project**: thai-legal-rag
**Context**: Rebuilding BM25 index from FAISS metadata after a re-index

## Pattern

Any search store that loads existing data in `__init__` will **append** rather than **replace** when you call a rebuild script. The store accumulates: 32k → 64k → 96k per run.

```python
class BM25Store:
    def __init__(self):
        self._load()  # ← loads existing file into self._corpus

    def add_batch(self, texts, metas):
        self._corpus.extend(...)  # ← appends to loaded data
```

## Fix

Wipe the index file before creating the store in rebuild scripts:

```python
if _BM25_FILE.exists():
    _BM25_FILE.unlink()
    print("Wiped existing BM25 index.")

store = BM25Store()  # now starts fresh
```

## Invariant Check

After any index rebuild: `count(rebuilt_index) == count(source_data)`

If count is 2× source → append trap. If count is less → truncation or batch error.

## Related

- `pipeline/build_bm25_index.py` — fixed `d3202cd`
- Same pattern applies to any persistent store: FAISS, vector DBs, etc.
