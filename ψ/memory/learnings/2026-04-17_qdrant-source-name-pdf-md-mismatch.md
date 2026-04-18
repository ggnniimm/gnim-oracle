# Qdrant Source_name Mismatch (.pdf vs .md) Silently Orphans Vectors

**Date**: 2026-04-17
**Context**: TC-037 consistently failed — doc 12602 was "missing" from Qdrant. Root cause: old chunks indexed under `.pdf` source_name, new indexer uses `.md` source_name. Force-reindex fixed it.
**Tags**: #qdrant #indexing #source-name #retrieval #debug

## Problem

When the indexer pipeline changes how it stores `source_name` in Qdrant payloads (e.g. from `doc.pdf` → `doc.md`), old chunks become orphaned:

- Old chunks stay in Qdrant under `.pdf` source_name
- New incremental index skips the file (chunk hashes already in dedup.db)
- Scroll/filter queries looking for `.md` source_name return 0 results
- Vector search may still hit old `.pdf` chunks (not deleted), but they may be stale or mis-matched

Result: the doc appears "missing" from Qdrant when searched by `.md` name, but 62 stale `.pdf` chunks are silently in the collection, potentially returning outdated content.

## Specific Case (doc 12602)

- `data/md_backup/003_กวจ_12602_...PDPA.md` — correct 5M threshold in สรุปข้อวินิจฉัย
- Qdrant scroll for source_name = `...PDPA.md` → 0 results
- Incremental index → "31 skipped" (hashes in dedup)
- `--force-reindex` output: "Deleted 62 vectors (source_name='...PDPA.pdf')" ← smoking gun

62 old `.pdf` chunks existed. The `.pdf` chunks apparently didn't surface for the TC-037 query via hybrid search. After force-reindex with `.md` source_name, BM25 matched "5,000,000" string → TC-037 PASS.

## Debugging Sequence (Better Order)

1. **Fuzzy search Qdrant first** — `MatchText(text='12602')` finds orphaned `.pdf` chunks if they exist
2. **Check dedup count** — `SELECT COUNT(*) WHERE source_id = file_id` shows if hashes registered
3. **Check Qdrant by payload fragment** — don't assume exact source_name, search by substring
4. **Force-reindex if mismatch found** — cleans old chunks and writes fresh ones with correct name

## Fix

```bash
QDRANT_URL=http://localhost:6333 THAI_RAG_DATA_DIR=$(pwd)/data \
  python3 pipeline/index_md_folder.py --dir data/md_backup --no-lightrag \
  --force-reindex --file "filename.md"
```

The force-reindex:
1. Deletes all Qdrant vectors where `source_name` matches the PDF filename
2. Deletes dedup entries for that file_id
3. Re-indexes fresh with `.md` source_name

## Broader Risk

Any doc that was indexed before the pipeline switched from `.pdf` → `.md` source_name convention may have this split. Audit: `curl Qdrant scroll` and check `source` payload field for `.pdf` suffix — those are orphaned old-format chunks. Recommend running `--force-reindex` on all docs once to normalize source_name convention.

## Files

- `pipeline/index_md_folder.py` — `--force-reindex` flag handles cleanup + re-index
- `data/dedup.db` — indexed_chunks table (hash, source_id, added_at)
- Qdrant `source` payload field — was `.pdf`, now `.md` convention
