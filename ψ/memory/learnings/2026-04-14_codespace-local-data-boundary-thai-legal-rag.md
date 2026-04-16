---
title: ## Codespace / Local Data Boundary
tags: [codespace, data-boundary, thai-legal, environment]
created: 2026-04-14
source: rrr: orientation-only 2026-02-19
---

# ## Codespace / Local Data Boundary

## Codespace / Local Data Boundary

Thai Legal RAG data (OCR cache, FAISS index) lives locally on Ming's machine, not in the repo or codespace. When working from a codespace without that data, `/tmp/thai-legal-rag/` will be empty and `law_*.json` cache files won't exist.

**Lesson**: Recognize the boundary fast. If config points to a data directory and it's empty, ask immediately — don't search for 10 minutes. The question is: "do you have the cache locally, or do we need to re-generate from Drive?"

**Work split**:
- Data-dependent: running --resplit, counting section differences, verifying fixes against cache
- Data-independent: writing comparison scripts, writing tests, reading/editing source code

When data is unavailable, pivot to data-independent work rather than staying blocked.

**Quick check**:
```python
cache = Path(os.getenv('THAI_RAG_DATA_DIR', '/tmp/thai-legal-rag')) / 'ocr_cache'
files = list(cache.glob('law_*.json'))
print(f'Law files: {len(files)}')
```

---
*Added via Oracle Learn*
