# Concurrent Index Rebuild Causes Dedup Race Condition

**Date**: 2026-03-09
**Source**: rrr: gnim-oracle/thai-legal-rag
**Confidence**: High (reproduced: 966→1230 sources after fix)

## Pattern

Running two index rebuilds concurrently (`rm -f + python index_md_folder.py`) causes a dedup.db race condition where one process's entries are seen by the other, resulting in 5500+ chunks being silently skipped. The resulting index has only 966/1230 sources instead of the full set.

## Root Cause

Both processes delete files and start fresh, but:
1. Process A starts, creates dedup.db, begins indexing files
2. Process B deletes dedup.db (A's handle stays on old unlinked file), creates new dedup.db
3. Process B processes files, saves to new dedup.db
4. But Process A also saved to the same filesystem path at some point, or the concurrent SQLite access caused corruption

The exact mechanism is unclear (Unix file handle semantics vs SQLite WAL mode), but the effect is consistent: ~5500 chunks are marked as "already indexed" in dedup.db despite not being in the FAISS index.

## Symptoms

- Eval score drops (44→40/48)
- `Total unique sources` in metadata is 966 instead of 1230
- Specific files (52101, 51349, ว126, ว130) have 0 chunks in FAISS but are marked as indexed in dedup.db
- `is_indexed()` returns True for chunks that aren't in the actual FAISS index

## Rule

**NEVER run concurrent index rebuilds.** Always wait for one to complete before starting another. If in doubt, check `ls -la data/dedup.db data/faiss_index/index.faiss` timestamps and verify both are from the same build.
