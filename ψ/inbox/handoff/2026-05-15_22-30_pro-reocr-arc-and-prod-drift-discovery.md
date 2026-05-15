# Handoff: Pro Re-OCR Arc + Prod-Local Code Drift Discovery

📡 Session: 8a4a9bfa | gnim-oracle | ~7h
**Date**: 2026-05-15 22:30
**Context**: Late session after morning hybrid-Pro deploy

## What We Did

### Pro re-OCR arc (ว124 → batch of 3 → batch of 19 in progress)
- **ว124** (19 pages): Flash 30KB → Pro 99KB, page 9 table recovered via `retry_failed_pages.py`. Local 66→118 chunks, prod 33→118.
- **batch of 3** (ว1052, ว477, ว56): Pro re-OCR with Circular schema (was wrongly using Ruling schema).
  - ว1052: 53 pages! (was thought to be 2-3) — network died at p40-53, recovered via retry. 32→474 chunks local+prod.
  - ว477: 32→11 (Flash over-produced, Pro stripped boilerplate)
  - ว56: 40→65 (Pro flagged "ว ๕" on p1 as possible OCR error vs filename ว ๕๖ — filename override corrected doc_number)
- **batch of 19** (`task byi8t7vx2`): IN PROGRESS — 6/19 done at session end, ETA ~60 more min.
- **Filename rename arc**: `+` form → `_` form (Drive truth) for ว1052/ว477/ว397/FAQ — orphans deleted post-OCR. Pattern matches existing `md-filename-must-match-drive` memory.

### Inactive flag work (5 files explicit + huge discovery)
- User requested: 5 "เพิกถอนผู้ทิ้งงาน" files flipped to `status: inactive` (ว139, ว159, ว181, ว235, ว270)
- Local force-reindex correctly deleted chunks (status-check active)
- **Prod required Qdrant API delete** — 158 chunks removed via FilterSelector

### 🚨 Major discovery: Prod-local code drift (5 weeks)
- Prod `md_loader.py` is dated **2026-04-02** vs local **2026-05-10** (commit `6c1377f` "add inactive status filter")
- **Prod doesn't have the `if status == inactive: return []` check** (3 lines missing)
- Last night's 14h 53m full re-index on prod indexed ALL 106 inactive files
- **101 inactive files / 4,707 chunks (13.5% of 34,703) are polluting prod RAG retrieval**
- Other src/ files also drift (qdrant_store, gemini_client, config, reranker, ocr) but only md_loader is a *correctness bug* — others are either dead code on prod (ocr.py is never called from streamlit), missing OCR-only features, or comment-only diffs

### Other findings
- Today's earlier batch 3 prod re-index task (`bx3z1uu3s`) showed exit 255 but actually completed inside container (chunks match local exactly)
- 1 learning memo committed: `c7c950b memory: 2026-05-15 retry_failed_pages pattern (ว124 p9 recovery)`

## Pending

- [ ] **STEP A**: Delete 4,707 inactive chunks from prod Qdrant via API (one filter call, ~1 min)
- [ ] **STEP B**: Surgical patch prod `md_loader.py` — `docker cp` + `docker commit` + `docker compose restart app` (~1 min, ~30s downtime)
- [ ] **STEP C**: Re-run prod eval to verify 77/84 holds after inactive cleanup (~30 min)
- [ ] **STEP D**: Wait for batch 19 OCR (`byi8t7vx2`) to complete, then cleanup orphans + force-reindex 19 files on local + prod
- [ ] **STEP E**: Write learning memo on prod-local drift detection pattern (deploy verification gap)

## Next Session

- [ ] Resume from batch 19 OCR result (check `/tmp/reocr_19.log` and `/tmp/reocr_19_results.json`)
- [ ] Execute A+B (cleanup + patch) BEFORE D (so batch 19 reindex benefits from the fix)
- [ ] Run eval as gate before declaring "deploy done"
- [ ] Consider broader: should we deploy other 5 src/ files? Currently safe to skip — all either dead-code-on-prod or comment-only. Defer until needed.

## Key Files

### Code / scripts
- `/Users/mingsaksaengwilaipon/gnim-oracle/ψ/lab/thai-legal-rag/src/ingestion/md_loader.py` — local has inactive check at line 153
- `/tmp/reocr_19.log` — live OCR progress
- `/tmp/reocr_19_results.json` — JSON summary (after OCR finishes)
- `/tmp/reocr_circulars_19.py` — re-OCR driver
- `/tmp/src_local/` + `/tmp/src_prod_extract/` on prod — diff workspace already prepared

### MDs flipped to inactive today (5)
- `กค_ว139_280866_การเพิกถอนรายชื่อผู้ทิ้งงาน.md`
- `กค_ว159_080868_การเพิกถอนคำสั่งผู้ทิ้งงาน.md`
- `กค_ว181_040968_การเพิกถอนคำสั่งผู้ทิ้งงาน.md`
- `กค_ว235_201068_การเพิกถอนคำสั่งผู้ทิ้งงาน.md`
- `กค_ว270_171268_การเพิกถอนคำสั่งผู้ทิ้งงาน.md`

### Batch 19 source files
- `ψ/lab/thai-legal-rag/data/md_backup/` — 19 circular MDs being re-OCR'd

### Prod
- `root@31.97.188.155:/app/thai-legal-rag/` — deploy target
- Container: `thai-legal-rag-app-1`
- Qdrant collection: `thai_legal_rag`

## Numbers to verify next session

| Metric | Now | After A | After B (no change) | After D (batch 19 reindex) |
|---|---|---|---|---|
| Prod total chunks | 34,703 | ~29,996 | ~29,996 | ~30,500 ± batch 19 delta |
| Inactive chunks on prod | 4,707 | 0 | 0 | 0 |
| Files inactive but indexed | 101 | 0 | 0 | 0 |
| Prod md_loader has inactive check | ❌ | ❌ | ✓ | ✓ |
