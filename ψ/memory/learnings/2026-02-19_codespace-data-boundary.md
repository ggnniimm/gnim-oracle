# Codespace / Local Data Boundary

**Date**: 2026-02-19
**Source**: rrr: orientation-only

## Pattern

Thai Legal RAG data (OCR cache, FAISS index) lives locally on Ming's machine, not in the repo or codespace. When working from a codespace without that data:

- `/tmp/thai-legal-rag/` will be empty (default `THAI_RAG_DATA_DIR`)
- `law_*.json` cache files won't exist
- Data-dependent tasks (running splits, comparing counts) can't proceed

## Lesson

**Recognize the boundary fast.** If config points to a data directory and it's empty, ask immediately — don't search for 10 minutes. The question is: "do you have the cache locally, or do we need to re-generate from Drive?"

## Work Split

| Data-Dependent | Data-Independent |
|----------------|------------------|
| Running --resplit | Writing comparison script |
| Counting section differences | Writing new tests |
| Verifying fixes against cache | Reading/editing law_extractor.py |

When data is unavailable, pivot to data-independent work rather than staying blocked.

## Quick Check

To verify environment readiness before starting data work:
```bash
python3 -c "
from pathlib import Path
import os
cache = Path(os.getenv('THAI_RAG_DATA_DIR', '/tmp/thai-legal-rag')) / 'ocr_cache'
files = list(cache.glob('law_*.json'))
print(f'Cache: {cache}')
print(f'Law files: {len(files)}')
"
```
