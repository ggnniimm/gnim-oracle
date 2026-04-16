---
title: ## MD Frontmatter Is the Source of Truth for Google Drive file_id
tags: [source-of-truth, qdrant, google-drive, md-frontmatter, file-id, data-integrity, thai-legal-rag]
created: 2026-04-14
source: 2026-04-14 learning
---

# ## MD Frontmatter Is the Source of Truth for Google Drive file_id

## MD Frontmatter Is the Source of Truth for Google Drive file_id

When multiple sources hold the same data (Drive file_id appears in xlsx, MD frontmatter, and Qdrant payload), establish which is the source of truth before patching anything.

**For thai-legal-rag**:
- **MD frontmatter (`file_id:`)** — source of truth ✅ (verified from Drive audit 2026-04-08)
- **`document_list.xlsx` col 8** — inventory tracker, often stale ❌ (1,268 IDs wrong out of 1,383 files)
- **Qdrant payload `file_id`** — derived, must always be patched from MD

**Rule**: Before patching Qdrant file_ids with any script, cross-check:
```python
# Quick sanity check: sample 10 files
for md, xlsx_id in zip(sample_mds, sample_xlsx_ids):
    md_id = get_frontmatter_id(md)
    assert md_id == xlsx_id, f"MISMATCH: {md.name}"
```
If mismatch → use MD as source of truth, always.

**Correct script**: Reads MD frontmatter directly, never uses xlsx.

**Always snapshot Qdrant before patching**:
```bash
curl -X POST http://{qdrant_ip}:6333/collections/thai_legal_rag/snapshots
```

---
*Added via Oracle Learn*
