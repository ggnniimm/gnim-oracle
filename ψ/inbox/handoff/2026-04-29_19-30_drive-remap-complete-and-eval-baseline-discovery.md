# Handoff: Drive Remap Complete + Eval Baseline Discovery

**Date**: 2026-04-29 19:30 BKK
**Session**: 057b8553 | gnim-oracle | ~9h 30m

## Where things stand

Today went from "deploy Drive ID remap" → "discover that local Qdrant has been double-indexed all along". Two big things landed:

### 1. Drive ID remap — fully deployed ✅

| | Before | After |
|---|---|---|
| Prod md_backup | 1,381 files (215 prod-only) | **1,233 files** (parity with local) |
| Prod Qdrant | 56,902 points | **27,849 points** (3072-dim) |
| Drive `file_id` payload | stale | fresh ✓ |
| 5 too-long files (>255B ext4 NAME_MAX) | excluded | renamed <120B + reindexed ✓ |

mwaprocure HTTP 200, retrieval verified.

### 2. Eval baseline ที่เคยเชื่อ = หลอก

Eval บน clean prod index = **65/80**. ก่อนหน้านี้ baseline บน local = 77/78. ดูเหมือน regression 17% — แต่ตรวจตัวเลขแล้วพบว่า:

```
Local Qdrant: ทุก chunk มี 2 copies (Counter({2: 396}))
Prod Qdrant: ทุก chunk มี 1 copy (Counter({1: 396}))
```

Local ถูก double-indexed มาตลอด — pipeline runs สะสม dupes โดย dedup ไม่ catch. eval pass rate `77/78` มาจาก top-K retrieval ที่ดึง chunk + clone เป็น 2 hits = effective surface area 2x → answers ดีขึ้นโดยบังเอิญ.

**Prod 65/80 = baseline จริง**. ไม่มี regression. มี discovery.

หลัง rename 5 ไฟล์ → 66/80 (TC-008 verified PASS). อีก 4 ไฟล์ที่ rename ไม่มี TC ที่อ้างถึงโดยตรงใน golden suite, เลยไม่ขยับ.

## What's pending for next session

### High priority — diagnose 13 remaining failures (true-baseline fails)

Failed cases on prod (besides TC-008, now PASS):
- TC-034 เงื่อนไขวิธีเฉพาะเจาะจง
- TC-035 เรียกค่าเสียหายเมื่อบอกเลิกสัญญา
- TC-039 ขอเพิ่มค่าจ้างเพราะค่าแรงขั้นต่ำเพิ่มขึ้น
- TC-046 ผู้ยื่นข้อเสนอเคยมีผลงานเสียหายร้ายแรง
- TC-051 ค่าใช้จ่ายจากการขยายเวลา
- TC-063 สัญญาทางปกครอง ไม่เป็นธรรม
- TC-064 อายุความ บอกเลิกสัญญา
- TC-065 ประมาทเลินเล่อร้ายแรง
- TC-066 ส่งงานไม่ครบ ตรวจรับแล้ว
- TC-067 ผู้ควบคุมงานต้องรับผิดหรือไม่
- TC-071 ม.97 vs ม.102 (known flaky)
- TC-074 สั่งการด้วยวาจา
- TC-075 ผู้ใช้น้ำสิทธิภาระจำยอม
- TC-076 ความหมายของค่าปรับ

**Diagnosis plan per TC**:
1. Run `--id TC-XXX -v --no-generate` on prod → see top-K retrieved
2. Compare to expected_sources → ถ้า expected ไม่ใน top-K = retrieval gap → cross-ref injection or rescue phrases
3. ถ้า expected อยู่ใน top-K แต่ generation ผิด must_contain = generator/prompt issue → maybe rule update

Pattern จาก past: `crossref-target-top-ranked-doc` learning. ดู `ψ/memory/learnings/2026-03-11_crossref-target-top-ranked-doc.md`

### Medium priority

- [ ] **Wipe + clean-reindex local Qdrant** to match prod truth — local 56K ปนเปื้อน dupes, future dev work จะหลอก
- [ ] **Update eval baseline** ใน MEMORY.md จาก "77/78 stable" เป็น "66/80 clean baseline (post-deduplication)"
- [ ] **(Ming)** rotate Gemini key — current key (`AIzaSyAw...1E8w`) ถูกพิมพ์ใน prod bash history ระหว่าง deploy

### Low priority

- [ ] (Ming-only) verify mwaprocure login flow บน browser
- [ ] consistency_check.py on real query (#29) — defer until after 13 fails diagnosed

## Key paths / commands

```bash
# Eval single TC verbose on prod (no generation)
ssh root@31.97.188.155 'docker exec thai-legal-rag-app-1 \
  python3 -u /app/pipeline/run_eval.py --id TC-034 -v --no-generate'

# Full eval prod (background, ~80 min)
ssh root@31.97.188.155 'nohup sh -c "docker exec thai-legal-rag-app-1 \
  python3 -u /app/pipeline/run_eval.py > /tmp/eval_<date>.log 2>&1" \
  > /dev/null 2>&1 & disown'

# Verify chunk distribution for any source
docker exec thai-legal-rag-app-1 python3 -c "..."  # see learning file
```

## Backups still in place

- Local: `/tmp/prod_md_backup_2026-04-29/` (30MB — original 1,381 prod MDs)
- Local: `ψ/archive/lightrag-2026-04-29/lightrag_data_2026-04-29.tar.gz` (64MB)
- Prod: Qdrant snapshot from 03:05 UTC, dedup.db.bak.2026-04-29, bm25.pkl.bak.2026-04-29, .env.bak.2026-04-29

## Session learnings written

- `ψ/memory/learnings/2026-04-29_drive-remap-deploy-gotchas.md` — openrsync/ext4/Gemini key/SSH gotchas
- `ψ/memory/learnings/2026-04-29_scope-creep-in-cleanup-tasks.md` — lightrag overstep (saved as feedback too)
- `ψ/memory/learnings/2026-04-29_double-indexed-eval-baseline.md` — the chunk-distribution discovery

## Important reminders

- **Local Qdrant = polluted** (double-indexed). Don't trust historical local eval results until wiped.
- **`source_name` ใน payload มาจาก `original_filename` frontmatter**, ไม่ใช่จาก filename บน disk → rename .md filename ปลอดภัย
- ext4 NAME_MAX = 255 bytes, Thai 3 bytes/char → keep filenames <250 bytes
