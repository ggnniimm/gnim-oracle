---
title: ## Dedup Systems Block Content Updates — Need Force-Reindex
tags: [dedup, indexing, qdrant, content-update, force-reindex]
created: 2026-04-14
source: rrr: gnim-oracle thai-legal-rag Qdrant migration 2026-03-14
---

# ## Dedup Systems Block Content Updates — Need Force-Reindex

## Dedup Systems Block Content Updates — Need Force-Reindex

Content-hash dedup prevents re-indexing of modified documents. When an MD file is edited (e.g., cross-ref injection), only NEW chunks get indexed. Unchanged chunks remain in vector store with old content. Old and new chunks coexist → retriever picks up stale data.

**Fix workflow for modified file**:
1. Delete from vector store: Scroll by `source_name` filter → delete matching points
2. Delete from dedup DB: Compute chunk hashes using EXACT same enrichment logic (metadata prefix + text) → delete from `indexed_chunks`
3. Re-index: run `index_md_folder.py` on the file

**Key details**:
- Dedup hash = `SHA256(metadata_prefix + chunk_text)` where prefix = `[ref_number | date | category]\n\n`
- Qdrant source field is `source_name` (not `source`)
- Use `MatchText` filter for substring matching in Qdrant scroll

**Also**: Position of cross-ref text matters. Moving "แก้ไขสัญญา" from last bullet to FIRST BOLD bullet in สรุปข้อวินิจฉัย changed TC from 0/3 to 3/3. LLMs anchor on opening statements in context chunks.

---
*Added via Oracle Learn*
