# Handoff: Prod Cleanup Complete (A+B+D+C) — 82/84

📡 Session: dc9581a3 | gnim-oracle | ~2h
**Date**: 2026-05-16 08:08
**Context**: Continuation of 2026-05-15 22:30 handoff (Pro re-OCR Arc + Prod Drift Discovery). Executed STEPs A, B, D, C in that order.

## What We Did

### STEP A — Delete inactive chunks from prod Qdrant (~1 min)
- Built normalized match (`.md`↔`.pdf`, `+`↔`_`) from 105 local inactive MDs against 1,380 prod source_names
- 87 matched, 18 unmatched (5 = ว*-เพิกถอน deleted yesterday + 13 never indexed)
- One `FilterSelector` delete via `MatchAny`: **3,686 chunks removed** (handoff predicted 4,707 — diff explained by yesterday's prior cleanup + normalization stragglers)
- Prod: 34,703 → **31,017** chunks
- GH #36 closed with execution notes

### STEP B — Surgical patch prod `md_loader.py` (~1 min)
- Confirmed clean 3-line diff (only the `if status == inactive: return []` block, no other prod-local divergence)
- `docker cp` local → container → `docker commit thai-legal-rag-app:patched-2026-05-16-inactive-filter` → `docker compose restart app`
- Backup pre-patch at `root@31.97.188.155:/tmp/md_loader_prod.bak.2026-05-16`
- Functional test inside container post-restart: inactive MD (ว139) → **0 chunks**; active sample (ว357) → **12 chunks** ✓
- GH #37 closed with execution notes

### STEP D — Batch 19 reindex + orphan cleanup (~30 min)
- Overnight batch 19 OCR (`byi8t7vx2`) finished 23:45 in 81.8min: **19/19 OK** (18 good + 1 review-needed `FAQ_ว_645_693`)
- 4 orphans (old `+` form) deleted from local + prod md_backup; Qdrant orphan chunks were already 0 on both sides
- Local force-reindex (14m40s): **240 new chunks, 103 dedup-skipped**. Local Qdrant: 56,551 → 28,963 (note: local is still double-indexed cruft, ignore for eval)
- Prod force-reindex via `docker exec -d`: **319 new chunks, 24 dedup-skipped, 14m36s**. All 19 verified indexed (650 chunks aggregate)
- Prod: 31,017 → **31,368** chunks (net +351, replacement math from Flash → Pro content)
- Script reported "Total in DB: 33659" — that's a stale internal buffer, real count is 31,368
- GH #39 closed with execution notes

### STEP C — Prod 84-TC eval (~25 min)
- Background: `docker exec -d` → `/tmp/eval_2026-05-16_post-cleanup.log`
- Result: **82/84 PASS**
- Failures: TC-067 (`must_contain ['ไล่เบี้ย','ประมาทเลินเล่อ']`), TC-074 (`must_contain ['ป.พ.พ.','ประมวลกฎหมายแพ่ง']`) — both known intermittents, LLM-variance type, not new regressions
- TC-081-084 (Pro-routed date-calc): **4/4 PASS** ✓ Hybrid routing healthy
- GH #38 closed with execution notes

### Housekeeping
- Committed yesterday's 3 untracked handoffs/outbox as `1abe138`
- Pushed 6 commits total (5 prior + this one) to `origin/main`
- Closed GH #36, #37, #38, #39

## Pending

### Open from this arc
- [ ] **STEP E** — Memory: prod-local code drift detection pattern (GH #40) — not yet written

### MEMORY.md hygiene
- [ ] Append new baseline line: "2026-05-16 post-cleanup, 82/84, prod 31,368 chunks, inactive filter live" — current `2026-05-15 morning 77/84` line is stale

### TC monitoring (defer)
- TC-067 / TC-074 — per `verify-before-fix-known-fail` feedback: run 2-3× standalone before applying memory-based fixes if they recur
- Both have known historical fixes (TC-074 was in 04-30 chunk-promotion arc) — investigate if persistent over multiple runs

## Next Session

- [ ] Write STEP E learning memo and close GH #40
- [ ] Append fresh baseline line to MEMORY.md (one line, replace the stale 2026-05-15 morning entry)
- [ ] Consider: is the local Qdrant cruft (28,963 chunks after reindex of just 19) worth a wipe-and-rebuild to make local eval trustworthy again? Currently `2026-04-29_double-indexed-eval-baseline.md` memo says don't trust local eval — but we keep hitting friction from it.
- [ ] If TC-067/TC-074 keep failing across sessions: investigate retrieval gap (cross-ref injection / chunk promotion) — not memory fix

## Key Files

### Code / scripts
- `ψ/lab/thai-legal-rag/src/ingestion/md_loader.py` (local has inactive check at line 153, prod now matches via image tag `patched-2026-05-16-inactive-filter`)
- `ψ/lab/thai-legal-rag/pipeline/index_md_folder.py` (force-reindex driver)
- `/tmp/prod_reindex_19.py` (host) + container `/tmp/prod_reindex_19.py` — driver used for prod reindex

### Logs / artifacts
- Prod eval log: `root@31.97.188.155:` `docker exec thai-legal-rag-app-1 cat /tmp/eval_2026-05-16_post-cleanup.log`
- Prod reindex log: same container path `/tmp/prod_reindex_19.log`
- Prod md_loader.py backup: `root@31.97.188.155:/tmp/md_loader_prod.bak.2026-05-16`
- Batch 19 OCR results: `/tmp/reocr_19_results.json` (host)
- Inactive source_name list: `/tmp/inactive_prod_sources.txt` (host + container)

### Prod state
- Container: `thai-legal-rag-app-1` on `root@31.97.188.155`
- Qdrant collection: `thai_legal_rag` — **31,368 chunks**, dim 3072
- Image tag with fix: `thai-legal-rag-app:patched-2026-05-16-inactive-filter`
- Inactive filter: live (verified functional)

## Numbers snapshot

| Metric | Value |
|---|---|
| Prod chunks (final) | 31,368 |
| Inactive chunks (final) | 0 |
| Eval score (final) | 82/84 |
| Local files inactive | 105 |
| Local files with active chunks | ~1,288 |
| Days saved by surgical patch (vs full re-index) | ~1 (avoided another 14h re-index) |
