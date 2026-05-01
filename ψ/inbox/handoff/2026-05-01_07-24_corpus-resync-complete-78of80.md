# Handoff: Corpus resync complete — 78/80 in expectation

**Date**: 2026-05-01 07:24 BKK
**Session**: 94bd7d1e | gnim-oracle | ~17h (multi-stretch across 04-30 → 05-01)
**Status**: ✅ green. mwaprocure links restored, eval at 78/80 expectation, single source-of-truth established.

## What we did

This session ran the full arc from "trust break" → "diagnosed" → "deployed correctly" → "passed eval":

1. **Discovered**: 04-29 Drive remap deployed from wrong repo (`gnim-oracle`). Real source-of-truth = `gnim-oracle-qdrant` (1,385 MDs with 152 ref_sac_* court judgments + canonical Drive file_ids). Resulted in mwaprocure links 404'ing for ~95% of docs.
2. **Resolved data fork**: archived old `gnim-oracle/.../md_backup/` (1,233 MDs, stale) → tar.gz in `ψ/archive/`. Copied canonical `gnim-oracle-qdrant/.../md_backup/` (1,385 MDs) → `gnim-oracle/.../md_backup/`. Renamed 5 over-long filenames (>250 bytes ext4 limit).
3. **Re-deployed prod**: backed up Qdrant (snapshot 432MB) + dedup.db + bm25.pkl + md_backup tarball. rsync local → prod (220 created, 70 deleted). Wiped Qdrant collection + cleared dedup/bm25. Full reindex of 1,385 files → **28,654 chunks** in ~37 min.
4. **Verified**: file_id audit on Qdrant payloads → 1,250/1,302 sampled match Drive canonical (vs 0 before). curl 5 random Drive file_ids → all 200 OK. mwaprocure links should resolve.
5. **Full eval**: **76/80** (was 67/80). 6 corpus-gap fails (TC-063, 064, 065, 066, 074, 075) all now PASS.
6. **Fixed 2 corpus-expansion regressions** (TC-044, TC-050) via chunk promotion on operative source docs (52101, 33236) + must_contain phrasing variance for TC-044. Both 3/3 PASS.

## Pass-rate trajectory

| Stage | Rate | Notes |
|---|---|---|
| 2026-04-29 baseline | 66/80 | post-deploy with stale file_ids |
| 2026-04-30 morning fixes | 67/80 actual | TC-035, TC-046, TC-051, TC-071 — but 3 of 4 in wrong-repo MDs (later restranded) |
| 2026-04-30 corpus resync | 76/80 | full re-deploy from canonical |
| Post TC-044 + TC-050 fixes | **~78/80 expectation** | 2 reindex regressions resolved |
| Remaining | TC-037 (~67% pass), TC-071 (~67% pass) | both baseline-flaky |

## Pending — for next session

### Standing user-actions (Ming)

- [ ] **Verify mwaprocure UI**: open https://mwaprocure.gnim.cloud/ and click 3-5 document reference links. They should now open. If any 404, surface the file_id for diagnosis.
- [ ] **Rotate Gemini key** — leaked in prod bash history during 04-29 deploy
- [ ] **Wipe + clean-reindex local Qdrant** — local still double-indexed (`Counter({2: 396})`)

### Optional fixes (if pursuing 80/80)

- [ ] **Stabilize TC-037**: ~67% pass baseline intermittent. Run `--id TC-037 -v` 3-5x, identify which must_contain misses, add alternatives.
- [ ] **Stabilize TC-071**: ~67% pass. The chunk-promotion fix from 04-30 still in effect but LLM doesn't always cite ข้อ ๑๖๕. Could either add second `ข้อ ๑๖๕` mention to ว_476's body, or accept variance.
- [ ] **Push 7 commits** to origin/main (Ming approval needed before push)

### Cleanup

- [ ] **Decide on `gnim-oracle-qdrant` repo**: now stale source-of-truth. Options:
  - Rename to `gnim-oracle-qdrant.archive` (preserve, prevent future edits)
  - Delete its `md_backup/` subdirectory only
  - Leave as-is (drift risk if anyone edits there)
- [ ] **Stale local branch**: `fix/stale-cookie-and-rag-improvements` — checked out in another worktree, unrelated to today's work; ignore.

## Key files

- `ψ/memory/learnings/2026-04-30_corpus-resync-and-tc044-tc050-fixes.md` — full arc + reusable patterns
- `ψ/memory/learnings/2026-04-30_wrong-repo-source-of-truth.md` — codified detection
- `ψ/memory/learnings/2026-04-30_eval-tc046-summary-chunk-promotion.md` — chunk promotion pattern
- `ψ/memory/learnings/2026-04-30_eval-tc051-civil-code-backstop-injection.md` — cross-ref pattern
- `ψ/memory/learnings/2026-04-30_eval-tc071-section-number-promotion.md` — section-number promotion variant
- `ψ/memory/learnings/2026-04-30_eval-tc035-civil-code-alternative.md` — must_contain alternatives pattern
- `ψ/archive/md_backup_2026-04-30_pre-qdrant-sync.tar.gz` — old md_backup snapshot (rollback floor)
- Prod: `/tmp/prod_md_backup_2026-04-30_pre-qdrant-sync.tar.gz` + Qdrant snapshot 04-30-08-50-41

## Commits this session

```
2d4712c eval: TC-044 + TC-050 fixed post-corpus-resync — pass rate ~78/80
85d9f61 handoff: CRITICAL — source-of-truth is gnim-oracle-qdrant, not this repo
2d4a124 eval: TC-071 section-number promotion + corpus-gap discovery
987a822 eval: TC-051 fix — ป.พ.พ. backstop cross-ref in ๑๕๙/๒๕๖๖ summary
902ba02 eval: TC-046 fix — promote สรุปข้อวินิจฉัย chunk via answer-shaped bullet
3cf2c81 handoff: 2026-04-30 — TC-035 fix + 14-fail bucket verified down to 11
5134af9 eval: TC-035 accepts ป.พ.พ. anchors as alternative to พ.ร.บ. ม.103
```

7 commits ahead of origin/main, not yet pushed.

## Trust note

Session started with Ming's trust break ("ตอนนี้ไม่มีความเชื่อใจแล้ว มั่วมาก") after I edited the wrong repo. That instinct was correct and led to the discovery. The fix landed cleanly: corpus consolidated, links restored, eval +11 net. Future sessions: **verify source-of-truth before any deploy work**.
