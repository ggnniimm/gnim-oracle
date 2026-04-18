---
title: Qdrant source_name mismatch (.pdf vs .md) silently orphans vectors — always use 
tags: [qdrant, indexing, source-name, retrieval, debug, pipeline, dedup, hybrid-search]
created: 2026-04-17
source: rrr: gnim-oracle
---

# Qdrant source_name mismatch (.pdf vs .md) silently orphans vectors — always use 

Qdrant source_name mismatch (.pdf vs .md) silently orphans vectors — always use fuzzy search to debug "missing" docs.

When indexer pipeline changes source_name convention (e.g. doc.pdf → doc.md in payload):
- Old chunks stay in Qdrant under .pdf source_name
- Incremental index skips file (hashes in dedup.db already)
- Scroll by exact .md source_name returns 0 → doc appears "missing"
- Old .pdf chunks may still be in collection but stale/mis-attributed

Debug order (better):
1. MatchText(text='doc_id_fragment') — fuzzy, finds orphaned chunks regardless of extension
2. Check dedup: SELECT COUNT(*) WHERE source_id = file_id
3. Only after confirming mismatch → run --force-reindex

Fix: --force-reindex deletes by source_name (pdf pattern), clears dedup, writes fresh .md chunks.

Specific case (2026-04-17): doc 12602 had 62 old .pdf chunks in Qdrant, 0 .md chunks. TC-037 consistently failed (5M threshold never in answer). Force-reindex fixed it — BM25 hit "5,000,000" string in fresh .md chunks.

Broader risk: any doc indexed before pipeline switched .pdf→.md convention may have this split. Audit: scroll Qdrant, filter source payload ending in .pdf — those are orphaned old-format chunks.

---
*Added via Oracle Learn*
