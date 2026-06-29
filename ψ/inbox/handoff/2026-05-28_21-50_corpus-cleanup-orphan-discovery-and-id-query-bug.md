# Handoff: Corpus Cleanup, Orphan Discovery, and ID-Query Retrieval Bug

**Date**: 2026-05-28 21:50 +07
**Session**: 2f2540db | gnim-oracle/thai-legal-rag | ~12h
**Context**: Long maintenance day — full retrospective × 2 written

## What We Did

### Morning: Inactive cleanup + 5 file push (retro 1: 20.03)
- Marked 4 หนังสือเวียน inactive (ว232, ว570, ว851/ว451, ว196 — cancelled by ว651, ว298, ว299)
- Deleted 773 old chunks directly from Qdrant (force-reindex silently fails for inactive files)
- Re-OCR'd ว189 + การลงทะเบียนฯ pushed from local 2.5-pro version (replacing prod 2.0-flash)
- Fixed ว_214 doc_number OCR error (ว224 → ว214, confirmed by Ming viewing PDF)
- Pushed 5 new MD files; fixed 10515 (was 2.0-flash with `/0` doc_number on prod)
- Created `scripts/sync_md.sh` (rsync push/pull/diff) — committed `ad01c31`
- Rebuilt BM25 from Qdrant (was double-indexed at 68,359; now 34,124)

### Evening: 17-file batch + orphan discovery (retro 2: 21.28)
- 17 files with size diff: pushed + force-reindex (14 active = 442 chunks net +188; 3 inactive = 0 correctly)
- Wasted 10 min on "0 chunks" symptom — assumed dedup bug, actually was `status: inactive` (saved lesson `check-filter-before-debug-empty`)
- **Major discovery**: 518 orphan files on prod (24 law section subdirs + 1 mof file), not in Qdrant but structured content
- **Almost-disaster averted**: sync_md.sh defaulted to `--delete` — `push` would have wiped all 518 orphans
- Hardened sync_md.sh: `--delete` now opt-in (committed `eb506d1`)
- Pulled prod → local: 1,387 → 1,889 files (orphans backed up)
- Started ID-query bug investigation (ว397 etc.)

### Final state
- Prod Qdrant: 34,312 chunks exact
- BM25: 34,312 docs (in sync)
- Local md_backup: full mirror of prod (incl. orphans)

## Discovered: ID-style Query Retrieval Bug

User asked about ว397 on production — LLM said "not found", but ว397 IS in corpus (12 chunks indexed).

**Test of 8 ว NNN docs** (rank when querying "ว NNN"):
| Doc | Rank | Date |
|---|---|---|
| ว 298, 299, 651, 189 | 1 ✅ | recent (2568-2569) |
| ว 397 | 10 ⚠️ | 2566 |
| ว 214, 110, 181 | MISS ❌ | 2563-2568 |

**Root cause**: For ว 397 — chunks ARE in pool (BM25 rank 1, vector rank 10) but rerank pushes them down. For ว 214, ว 110 — chunks are NOT in retrieval pool at all (vector + BM25 miss).

**Option 4 (filename injection in reranker)** is the proposed fix: detect "ว NNN" pattern in query → query Qdrant with `MatchText` filter on source_name → inject chunks into rerank pool. Single file change (`src/retrieval/reranker.py`). NOT yet implemented.

## Pending

- [ ] Implement Option 4: filename injection for ID-style queries (ว NNN) in `src/retrieval/reranker.py`
- [ ] Run 82-TC eval baseline after Option 4 to check regression
- [ ] Verify ว 214, ว 110, ว 181, ว 397 all return rank 1 with the fix
- [ ] Build + deploy Docker image with reranker fix
- [ ] Decide what to do with 518 orphan files (keep / re-index / prune)
- [ ] Investigate if law section files (subdirs) should be indexed into Qdrant — they have structured metadata
- [ ] Add BM25 vs Qdrant health check to `drift_check.sh` (`bm25.count == qdrant.exact_count`)
- [ ] Consider extending Option 4 pattern to "มาตรา NNN" / "ข้อ NNN" / generic doc_number queries
- [ ] Add log warning in force-reindex pipeline when file is inactive

## Next Session

- [ ] Start with `/recap` to reload context
- [ ] Implement filename-injection boost in reranker.py per Option 4 plan
- [ ] Test against 8 ว NNN sample on prod (verify all rank 1)
- [ ] Run full 84-TC eval — compare against baseline 82/84 PASS
- [ ] Deploy if no regression
- [ ] Add prod smoke query: "ว 397" → should return rank 1

## Key Files

- `src/retrieval/reranker.py` — code to modify for Option 4
- `src/config.py` — RECENCY_BOOST = 0.05, BM25_WEIGHT
- `scripts/sync_md.sh` — sync utility (now --delete is opt-in)
- `data/md_backup/` — 1,889 MD files (incl. orphan subdirs)
- `eval/golden_test_cases.json` — 84 TCs baseline
- `ψ/memory/retrospectives/2026-05/28/20.03_corpus-inactive-cleanup-sync.md`
- `ψ/memory/retrospectives/2026-05/28/21.28_17file-batch-orphans-discovery.md`
- `ψ/memory/learnings/2026-05-28_qdrant-soft-delete-approximate-count.md`
- `ψ/memory/learnings/2026-05-28_destructive-defaults-are-tech-debt.md`

## Production State

- Server: 31.97.188.155 (root@) — SSH often blocked by ISP, use hotspot
- App container: `thai-legal-rag-app-1` | Qdrant container: `thai-legal-rag-qdrant-1`
- Collection: `thai_legal_rag` | exact count: **34,312**
- BM25: `/app/data/bm25_index/bm25.pkl` (34,312 docs)
- Backup: `bm25.pkl.bak.pre-inactive-2026-05-28` (158MB, pre-rebuild)
