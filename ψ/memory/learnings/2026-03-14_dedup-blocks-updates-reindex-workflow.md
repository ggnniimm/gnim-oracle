# Dedup Systems Block Content Updates — Need Force-Reindex

**Date**: 2026-03-14
**Source**: rrr: gnim-oracle (thai-legal-rag Qdrant migration)
**Tags**: dedup, indexing, qdrant, content-update, pipeline

## Pattern

Content-hash dedup prevents re-indexing of modified documents. When an MD file is edited (e.g., cross-ref injection), only NEW chunks (with changed text) get indexed. Unchanged chunks are skipped by dedup but their OLD vectors in the vector store still point to pre-edit content. Result: old and new chunks coexist, retriever picks up stale data.

## Fix Workflow

To properly re-index a modified file:

1. **Delete from vector store**: Scroll by `source_name` filter → delete matching points
2. **Delete from dedup DB**: Compute chunk hashes using the EXACT same enrichment logic (metadata prefix + text) → delete from `indexed_chunks` table
3. **Re-index**: Run `index_md_folder.py` on the file — now all chunks are treated as new

## Key Details

- Dedup hash = `SHA256(metadata_prefix + chunk_text)` where prefix = `[ref_number | date | category]\n\n`
- Qdrant source field is `source_name` (not `source`)
- Use `MatchText` filter for substring matching in Qdrant scroll
- BM25 index has no delete — stale entries persist (not critical due to content dedup at retrieval)

## Lesson

Position of cross-ref text matters more than repetition. Moving "แก้ไขสัญญา" from last bullet to **first bullet with bold** in สรุปข้อวินิจฉัย changed TC-039 from 0/3 to 3/3. LLMs anchor on opening statements in context chunks.
