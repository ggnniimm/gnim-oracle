---
title: ## Drive File ID Audit and Cross-Day Data Integrity Workflow
tags: [drive, rag, data-integrity, bm25, qdrant, thai-legal-rag, audit]
created: 2026-04-14
source: Oracle Learn
---

# ## Drive File ID Audit and Cross-Day Data Integrity Workflow

## Drive File ID Audit and Cross-Day Data Integrity Workflow

### Context
Thai Legal RAG — Google Drive file_id audit (2026-04-08/09). 40 broken links across 1,383 MD files.

### Pattern: Drive Folder Mapping Is Tribal Knowledge
Document Drive folder structure with IDs. Without it, matching new PDFs to folders requires domain expert. Use `folder_mapping.json` or a column in `document_list.xlsx`.

### Pattern: Drive OAuth Token Expiry
"Drive API not enabled" error may actually be stale OAuth token, not disabled API. Always try `token refresh` first. Token at `token.json` — refresh if expired.

### Pattern: startswith Matching for Thai Filenames Is Fragile
`กฎกระทรวง+กำหนดพัสดุ` matches both short and long versions with startswith. Need exact matching or suffix exclusion.

### Pattern: Dedup Keys Are Drive file_ids, Not Filenames
BM25/dedup stores use file_id as source_id. When patching Qdrant by file_id, must also:
1. Delete dedup entries keyed by old file_ids
2. Re-index to create new entries
3. BM25 has no incremental delete — full rebuild required after any deletion

### Pattern: Gemini 503 Is Per-Endpoint
Classification may pass while extraction fails — different capacity pools. Wait a day before re-running eval if 503 storm hits many TCs. Don't panic-diagnose eval failures during infra incidents.

### Pattern: BM25 Full Rebuild From Qdrant
```python
# scroll all Qdrant points → rebuild BM25 pickle
bm25_store.rebuild_from_qdrant(qdrant_client)
```
Only safe way to remove stale BM25 entries after Qdrant deletion.

---
*Added via Oracle Learn*
