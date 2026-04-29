# Handoff: Drive ID Remap — Production Deploy Pending

**Date**: 2026-04-29 09:40
**Session**: 9de6b5ad | gnim-oracle
📡 Session: 9de6b5ad | gnim-oracle

## Status

The Drive ID remapping work was finished locally on 2026-04-08 (1,113 file_ids verified HTTP 200). The "remaining: deploy to production" item in MEMORY turned out to be more involved than the wording implied — local and prod have diverged by 215 files and need a Qdrant re-index, not just a payload patch.

This session **audited the divergence** and **documented the deploy plan**. No prod changes were made.

## What we found (verified 2026-04-29 09:30)

| | Local | Prod |
|---|---|---|
| MD files | 1,233 | 1,381 |
| Qdrant points | 56,191 | 56,902 |

215 files only on prod, breakdown:
- **152 `ref_*` court rulings** — Ming intentionally archived 9 เม.ย. (commit `2ab867e`). Archive preserved at `gnim-oracle-qdrant/ψ/archive/data_with_ac/md_backup/`. 152/152 verified ✓
- **59 `+`-named duplicates** — Local has `_`-separator versions instead
- **4 unicode-corrupted filenames** — Should be removed

67 files only on local — renames (35) + new content (~32).

## Pending — for next session

Full plan in `~/.claude/projects/.../memory/project_drive_id_remapping.md`. TL;DR:

- [ ] **Pre-flight** — confirm Qdrant snapshot API works on installed version
- [ ] **Pre-flight** — decide: full wipe+re-index (clean, ~30–60 min downtime) vs surgical Qdrant API patch (no downtime, leaves orphan chunks)
- [ ] **Phase 1** — backup prod MDs to `/tmp/prod_md_backup_<date>/` + Qdrant snapshot
- [ ] **Phase 2** — `rsync -avz --delete --exclude='.DS_Store' --exclude='._*'` from local `data/md_backup/` to prod
- [ ] **Phase 3** — wipe Qdrant collection, clear `data/dedup.db`, run `pipeline/index_md_folder.py` from app container
- [ ] **Phase 4** — verify points_count ≈ 56K, click sample เอกสารอ้างอิง links

## What was done this session (already committed + pushed)

- Cleanup: archived `feat/claude-design-ui` as tag, merged dependabot PR #23 (26/28 vulns)
- Built `scripts/consistency_check.py` — RAG answer consistency tester with `--save-tc` candidate generation
- Fixed suspended GEMINI_API_KEY in `gnim-oracle/.env` (backup at `.env.bak.2026-04-29`)
- Removed misdiagnosed `streamlit-first-question-lost` memory (was Ming's intentional consistency testing)
- Wrote retro: `ψ/memory/retrospectives/2026-04/29/08.25_loose-ends-cleanup.md`

## Important reminders

- Need ~1.5 hr block with prod downtime tolerance — don't start in middle of workday
- Production has no git — verify `pipeline/index_md_folder.py` exists in app container before Phase 3
- macOS `.DS_Store` / `._*` files MUST be excluded from rsync (per `learnings_hostinger_vps_deploy.md`)
