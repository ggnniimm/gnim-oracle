---
title: ## Qdrant Migration and Dedup-on-Update Footgun
tags: [qdrant, rag, indexing, migration, thai-legal-rag, dedup]
created: 2026-04-14
source: Oracle Learn
---

# ## Qdrant Migration and Dedup-on-Update Footgun

## Qdrant Migration and Dedup-on-Update Footgun

### Context
Thai Legal RAG — FAISS → Qdrant migration (2026-03-14).

### Pattern: Dedup Prevents Updates (Not Just Duplicates)
Append-only dedup systems (hash-based) prevent re-indexing unchanged chunks — but also prevent updated content from replacing old vectors when a file changes. Old vectors stay in Qdrant alongside new ones.

**Symptom**: Cross-ref injections not appearing in retrieval results despite being in the MD file.

**Fix**: Force-reindex workflow:
1. Scroll Qdrant by source_name filter → delete matching points
2. Compute chunk hashes using exact same enrichment logic as indexer
3. Delete from dedup DB
4. Re-index

**Prevention**: Add `--force-reindex --file X.md` as first-class operation.

### Pattern: Section-Level Law Files Not Indexed
Section-level law files in subfolders aren't picked up by top-level `*.md` glob. Need explicit subfolder patterns or recursive glob.

### Pattern: Qdrant Local Mode Warnings
Local mode prints `UserWarning` for collections >20K points. Use Docker mode for production:
- Removes warnings
- Better performance
- Supports selective delete natively

### Pattern: Transitional Law Context Must Be Explicit in MD
If a court case applies old law due to transitional provisions, the MD file must state WHY. Otherwise RAG will use the old legal number (e.g., 1-year statute) to answer current questions. Add note: "ใช้ อายุความ 1 ปี เพราะเหตุการณ์เกิดก่อน พ.ร.บ.ฉบับที่ 5 มีผล (28 ก.พ. 2551)".

---
*Added via Oracle Learn*
