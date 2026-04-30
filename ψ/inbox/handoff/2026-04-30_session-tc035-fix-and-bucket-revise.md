# Handoff: TC-035 fix + 13-fail bucket revised (2026-04-30)

**Session**: 94bd7d1e | gnim-oracle | ~3h
**Date**: 2026-04-30 ~02:00 BKK

## What landed

### Pass rate: 66/80 → **69/80** ✅

| TC | What changed |
|---|---|
| TC-035 | `must_contain` expanded to accept any valid legal anchor: ม.103 (พ.ร.บ.) OR ม.391/222 (ป.พ.พ.) OR ข้อ 183 (ระเบียบ). 3/3 PASS post-fix. |
| TC-034 | Verified **stable** 3/3 PASS — handoff's "FAIL" was one-time variance |
| TC-039 | Verified **stable** 3/3 PASS — same |

### Bookkeeping

- Yesterday's session trail committed (`d03be8d`): handoff + 2 learnings + retro
- MEMORY.md eval baseline updated: 77/78 stale → 69/80 clean truth
- 14-TC diagnosis bucket saved: `ψ/memory/learnings/2026-04-30_eval-13-fails-bucketed.md`
- TC-035 fix learning saved: `2026-04-30_eval-tc035-civil-code-alternative.md`

## Real remaining fails: 11 (down from 13/14 in original handoff)

After verification + TC-035 fix:

| Bucket | TCs | Fix-shape |
|---|---|---|
| **Citation/source-promotion needed** | TC-051, TC-071, TC-074 | Cross-ref injection or rescue phrase — expected source not in top-K |
| **Substantive content gap** | TC-046 (newly reclassified), TC-063, TC-064, TC-065, TC-067, TC-075, TC-076 | Per-TC retrieval-vs-content drill |
| **Liability term missing** | TC-066 | Likely cross-ref to ม.102/103 chunk |

### TC-046 reclassification (key finding)

Was in "intermittent" bucket. 3/3 FAIL today. The earlier PASS was the outlier. Source ว130/2569 has TWO operative clauses (6.5 ชี้แจง rights + 6.6 no-reject rule), LLM only surfaces 6.6. Missing the ชี้แจง dimension that the question asks about. Fix: cross-ref injection in ว130's สรุปข้อวินิจฉัย, or rescue phrase on `"ความเสียหายร้ายแรง"+"คณะกรรมการ"`.

## Pending for next session

### Quick wins (30 min)

- [ ] **TC-046 fix**: cross-ref or rescue phrase for ว130 ชี้แจง dimension. Source content already there, just chunk-selection issue.
- [ ] **TC-051 chunk probe**: 2/4 retrieved court judgments have `ป.พ.พ.`, 2/4 don't. Identify which chunk landed in context — prompt fix or cross-ref.

### Heavier (~30 min/TC)

- [ ] **TC-071 + TC-074**: cross-ref injection — expected sources `61864` / `ref_sac_o_16_2547` not in top-K
- [ ] 6 substantive gaps: TC-063, 064, 065, 067, 075, 076 — each needs `--no-generate -v` then per-TC strategy

### Standing reminders (Ming-action)

- [ ] **Rotate Gemini key** — current key was typed in prod bash history during 04-29 deploy
- [ ] **Wipe + clean-reindex local Qdrant** — local still double-indexed (`Counter({2: 396})`)
- [ ] (optional) verify mwaprocure browser login

## Key paths / commands

```bash
# Single TC verbose on prod
ssh root@31.97.188.155 'docker exec thai-legal-rag-app-1 \
  python3 -u /app/pipeline/run_eval.py --id TC-XXX -v'

# Surgical eval edit on prod (via Python — JSON-safe)
ssh root@31.97.188.155 'cd /app/thai-legal-rag/pipeline && cp golden_test_cases.json golden_test_cases.json.bak.YYYY-MM-DD && python3 - <<PY
... # see TC-035 fix in 2026-04-30_eval-tc035-civil-code-alternative.md
PY'

# Search source MD content
ssh root@31.97.188.155 'docker exec thai-legal-rag-app-1 grep -n "PHRASE" /app/data/md_backup/FILE.md'
```

## Gotchas captured

- **Local-vs-prod golden_test_cases.json gap**: local is 1455 lines, prod 1406. Local has ~50 lines of unverified changes ahead of prod. **Don't scp the whole file** — surgical edits only.
- **Prod has TWO copies**: `pipeline/golden_test_cases.json` (live, mounted to container) + `eval/golden_test_cases.json` (artifact). Container reads `/app/pipeline/...`. Update only `pipeline/`.
- **SSH port 22 ISP-blocked from home WAN**: switch to hotspot when prod unreachable on port 22 but HTTPS:443 works. App-layer reachability ≠ SSH reachability.
- **grep with Thai char ranges fails inside container**: `[ก-๙]` regex breaks with "Invalid collation character" in prod docker — use literal Thai strings instead.
