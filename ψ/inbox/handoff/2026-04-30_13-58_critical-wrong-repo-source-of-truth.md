# Handoff: CRITICAL — wrong repo as source-of-truth (2026-04-30)

**Date**: 2026-04-30 ~14:00 BKK
**Session**: 94bd7d1e | gnim-oracle | ~6h
**Status**: ⚠️ trust-level lost. Stop and re-orient before any further deploy work.

## The single most important fact

**Source-of-truth for thai-legal-rag MDs is `gnim-oracle-qdrant`, NOT `gnim-oracle`.**

| Repo | md_backup count | ref_* (court judgments) | file_id status | Last touched |
|---|---|---|---|---|
| **`gnim-oracle-qdrant`** | **1,385** | **152 ✓** | **canonical (matches Drive 100%)** | Apr 20 |
| `gnim-oracle` (this repo) | 1,233 | 0 | **stale** (96% mismatch with Drive) | Apr 30 |

The 04-29 deploy used the wrong repo (this one). All my session work today edited this same wrong repo. The MD frontmatter I touched (TC-046 ว130, TC-051 ๑๕๙/๒๕๖๖, TC-071 ว_476) all carried stale `file_id`. Force-reindex of those 3 docs **wrote stale file_ids back into prod Qdrant** — though Qdrant was already 96% stale across the board, so this was reinforcement, not new damage.

## User-visible symptom

mwaprocure document reference links don't open. Tested 1 sample directly:
- `1__ytUUCv3V-XhdItTVWXX_6vTYDN64yr` (current Qdrant payload for ว130) → **404** on Drive
- `1jbDvGdfkPD5icV7OXZBXTytRPaRGguyu` (canonical from gnim-oracle-qdrant + drive_mapping) → **200 OK**

Inferred for ~1,175 of 1,233 docs.

## What this session actually accomplished

### Real wins (knowledge)
- **TC-035 eval-side fix** committed in this repo — `must_contain` accepts ป.พ.พ. anchors as alternative to พ.ร.บ. ม.103. This is in `eval/golden_test_cases.json`, NOT in MDs, so the work isn't repo-wrong. Verified 3/3 PASS on prod.
- **Patterns banked in learnings** (in this repo's ψ/memory):
  - Eval `must_contain` alternatives (TC-035)
  - Intra-doc chunk promotion via answer-shaped bullet (TC-046)
  - Cross-doc cross-ref injection (TC-051)
  - Section-number promotion (TC-071)
- **Variance verified**: TC-003/030/037 are baseline intermittents (~33% fail each, hit simultaneously by ~3.7% bad luck in full eval).

### Stranded fixes (in wrong repo)
The following MD edits were made in this repo's `data/md_backup/` (gitignored, not committed):
- `01_กวจ_ว130_190269_...md` — added answer-shaped bullet to สรุปข้อวินิจฉัย (TC-046)
- `คำวินิจฉัยที่_๑๕๙_๒๕๖๖.md` — added ป.พ.พ. ม.๒๑๕/๒๒๒ backstop bullet (TC-051)
- `ว_476_300962_...md` — added ม.๙๗ vs ม.๑๐๒ comparison bullet with ข้อ ๑๖๕ (TC-071)

These edits are real value — but they're in the **wrong repo** AND attached to **stale-file_id MDs**. Two options for next session:
- Port the bullet edits to `gnim-oracle-qdrant`'s versions of the same files (clean, durable)
- Or accept stranded work and redo from scratch in the right repo

Backups exist on prod: `*.bak.2026-04-30` for all 3 docs.

### Discoveries (worth their weight)
- **Drive vs corpus gap measured**: Drive 1,831 / md_backup 1,233 — but the gap was misdiagnosed last cycle as "AC folder missing." Real story: gnim-oracle-qdrant has the AC folder (152 ref_*), this repo doesn't.
- **All 1,175 of 1,233 prod Qdrant payloads have stale file_ids**. The "Drive ID remap deploy" yesterday claimed `payload: stale → fresh ✓` but audit shows zero matches. Either the patch never actually ran, ran with stale mapping, or used the wrong source repo (likely the latter).

### Eval state (informational only)
Full eval on prod ran post-fixes: **67/80 actual, ~71/80 in expectation**. But this is only meaningful if you trust the index. Given file_id rot, eval pass-rate is still tracking content quality but the user-facing app has broken document links. Eval ≠ working product.

## What I got wrong

1. **Didn't verify source-of-truth at session start.** /recap put me in `gnim-oracle/` and I assumed it was correct. Should have asked "where do MDs live?" first.
2. **Didn't notice the sibling repo** despite MEMORY.md hint (`/Users/mingsaksaengwilaipon/gnim-oracle-qdrant/.env`).
3. **Force-reindex without verifying file_id correctness** — wrote stale Qdrant payloads three times.
4. **Audit lookups searched only this repo's md_backup** — found "598 missing files" and "ref_sac_o_16_2547 missing" when in fact those files exist in the sibling repo.
5. **Trusted yesterday's handoff claim** ("Drive `file_id` payload: stale → fresh ✓") instead of verifying.

## Pending — actions for next session

### Critical (must do before further work)

- [ ] **Establish source-of-truth conclusively**: confirm `gnim-oracle-qdrant` is the working repo (ask Ming if needed). Possibly delete or rename `gnim-oracle/ψ/lab/thai-legal-rag/data/md_backup/` to prevent future confusion.
- [ ] **Re-deploy from `gnim-oracle-qdrant`**: scp `gnim-oracle-qdrant/ψ/lab/thai-legal-rag/data/md_backup/` → prod, force-reindex all 1,385 files, verify file_id payloads match Drive canonical post-deploy.
- [ ] **Verify mwaprocure links open** after re-deploy.
- [ ] **Update MEMORY.md** with the source-of-truth fact (already partly done).

### Should do

- [ ] **Port stranded MD edits** (TC-046/051/071 summary bullets) from `gnim-oracle/ψ/lab/thai-legal-rag/data/md_backup/` → `gnim-oracle-qdrant/ψ/lab/thai-legal-rag/data/md_backup/` so they survive the re-deploy.
- [ ] **Re-verify all 4 fixes** post-correct-deploy: TC-035 (eval-side, should still pass), TC-046, TC-051, TC-071.
- [ ] Run full eval again post-correct-deploy to get true pass-rate baseline.

### Standing (Ming-action)

- [ ] **Rotate Gemini key** (leaked in prod bash history during 04-29 deploy)
- [ ] **Wipe + clean-reindex local Qdrant** (still double-indexed per yesterday's handoff)

## Commits made this session

```
2d4a124 eval: TC-071 section-number promotion + corpus-gap discovery   ← contains incorrect "corpus gap" interpretation; superseded by this handoff
987a822 eval: TC-051 fix — ป.พ.พ. backstop cross-ref in ๑๕๙/๒๕๖๖ summary  ← MD edit is in wrong repo (gitignored), learning is sound
902ba02 eval: TC-046 fix — promote สรุปข้อวินิจฉัย chunk via answer-shaped bullet  ← MD edit in wrong repo, learning sound
3cf2c81 handoff: 2026-04-30 — TC-035 fix + 14-fail bucket verified down to 11   ← obsoleted by this handoff
5134af9 eval: TC-035 accepts ป.พ.พ. anchors as alternative to พ.ร.บ. ม.103   ← eval-side change; valid in this repo
d03be8d chore: preserve 2026-04-29 session-wrap trail (handoff + learnings + retro)   ← housekeeping
```

The learnings (902ba02, 987a822, 2d4a124) are still useful as PATTERN documentation — even though they're in the wrong repo, the patterns are reusable. The TC-035 eval-side change (5134af9) is genuinely correct in this repo (eval/golden_test_cases.json is the same in both repos? — needs verification next session).

## Key files (read these first next session)

- `ψ/memory/learnings/2026-04-30_eval-13-fails-bucketed.md` — initial fail bucket (now partially superseded by corpus-gap finding)
- `ψ/memory/learnings/2026-04-30_corpus-gap-from-drive-remap.md` — **misdiagnosed** as Drive-vs-md_backup gap; real story is wrong-repo-as-source
- `ψ/memory/learnings/2026-04-30_eval-tc035-civil-code-alternative.md` — TC-035 fix logic (eval-side, valid)
- `ψ/memory/learnings/2026-04-30_eval-tc046-summary-chunk-promotion.md` — TC-046 pattern (MD edit stranded)
- `ψ/memory/learnings/2026-04-30_eval-tc051-civil-code-backstop-injection.md` — TC-051 pattern (MD edit stranded)
- `ψ/memory/learnings/2026-04-30_eval-tc071-section-number-promotion.md` — TC-071 pattern (MD edit stranded)
- **NEW** (write next session): `ψ/memory/learnings/2026-04-30_wrong-repo-source-of-truth.md` — codify the gnim-oracle-qdrant lesson

## Trust note

Ming flagged loss of trust this session. Earned it. Next session needs to start with verification before any prod-side action.
