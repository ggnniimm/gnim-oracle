---
title: # MD Frontmatter Is Source of Truth for Drive file_id
tags: [qdrant, drive, source-of-truth, patch, production-safety]
created: 2026-04-14
source: Oracle Learn
---

# # MD Frontmatter Is Source of Truth for Drive file_id

# MD Frontmatter Is Source of Truth for Drive file_id

## Core Rule
When Qdrant payloads and xlsx inventory disagree on Drive file_id, trust MD frontmatter — not xlsx.

Hierarchy:
1. **MD frontmatter** (`file_id:`) — authoritative, written at OCR time
2. **Qdrant payload** (`file_id` field) — derived from MD at index time
3. **xlsx document_list** — stale inventory, updated manually

## Before Mass-Patching Qdrant
Always take a snapshot first:
```bash
curl -X POST http://localhost:6333/collections/{collection_name}/snapshots
# Download and save before running any patch script
```

## Cross-Check Sources Before Patching Production
Compare MD frontmatter vs Qdrant payload vs xlsx — all three may disagree.
Don't rely on any single source. Script should:
1. Read MD files as ground truth
2. Query Qdrant to see current state
3. Compare before patching

## Script Env Vars
Use `os.environ.get()` not hardcoded constants. Scripts that patch production must read env at runtime:
```python
# ❌ hardcoded
QDRANT_URL = "http://localhost:6333"

# ✅ runtime
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
```

## Qdrant Payload State ≠ MD File State
After re-OCR or re-linking MD files, Qdrant payloads hold stale data until force-reindexed.
Verify independently: `grep -r "file_id:" data/md_backup/ | head` vs `curl .../points/{id}`.

From: `ψ/memory/retrospectives/2026-04/14/18.51_qdrant-file-url-patch.md`

---
*Added via Oracle Learn*
