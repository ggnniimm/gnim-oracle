---
title: ## LightRAG Indexing + Data Migration Lessons (2026-02-13)
tags: [lightrag, ocr-cache, data-migration, python, indexing, library-bugs]
created: 2026-04-14
source: retro: 2026-02-13 lightrag-indexing
---

# ## LightRAG Indexing + Data Migration Lessons (2026-02-13)

## LightRAG Indexing + Data Migration Lessons (2026-02-13)

**OCR cache key format**: Cache file = `sha256(file_id)[:16].hex() + ".json"` — NOT full hash and NOT `.md`. Deleting by `.md` extension silently fails, leaving old cache intact.

**LightRAG v1.3.1 bugs**:
- `pipeline_status` needs `history_messages: []` initialized before `del` (patch line 846 in `lightrag.py`)
- `gpt_4o_mini_complete` was removed — use custom `llm_model_func` instead
- `tiktoken` and `pipmaster` must be installed separately

**Data migration = multiple layers**: Verify every layer: cache → OCR output → saved file → index. Each transition can silently corrupt the next.

**Library bug patching is brittle**: Patching `/usr/local/python/.../lightrag/lightrag.py` directly breaks on codespace reset or package upgrade. Pin version or fork in requirements.txt instead.

**LightRAG indexing is opaque**: 80 minutes for 24 files with no per-file progress detail. If it fails mid-run, resume behavior is unclear — need visibility into progress.

---
*Added via Oracle Learn*
