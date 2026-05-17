---
date: 2026-05-17
tags: [git, prod-sync, local-first, architecture]
project: thai-legal-rag
---

# Reconcile Before Rebuild — Snapshot prod ก่อนเริ่ม Local-first

## Pattern

ก่อน switch ไป Local-first model (หรือ rebuild image จาก local) ต้อง snapshot prod ก่อนเสมอ แล้ว diff กับ local อย่างละเอียด เพื่อค้นหา stranded code ที่มีคุณค่าและยังไม่อยู่ใน git

## เหตุผล

เมื่อ prod กับ local drift กันมานาน (กรณีนี้: 5+ สัปดาห์, 595 บรรทัดใน ocr.py เท่านั้น) prod อาจมี:
- Code ที่เคยใช้งานจริงและยังไม่ได้ commit (`pipeline/run_eval.py`)
- Bug fix ที่ทำ inline แล้วลืม push กลับ
- Config ที่ evolved แตกต่างจาก local

ถ้า rebuild image จาก local โดยไม่ snapshot ก่อน = สูญเสีย stranded code ทั้งหมดโดยไม่รู้ตัว

## วิธีทำ

```bash
# 1. Snapshot prod → local (gitignored directory)
ssh root@PROD_HOST 'docker exec APP_CONTAINER tar c -C /app src pipeline app requirements.txt' \
  | tar x -C prod-snapshot/

# เพิ่ม prod-snapshot/ ใน .gitignore

# 2. Diff รายไฟล์
diff -r prod-snapshot/src/ src/ --brief
diff -r prod-snapshot/pipeline/ pipeline/ --brief
diff -r prod-snapshot/app/ app/ --brief

# 3. Decision matrix ต่อไฟล์:
#   - identical → no action
#   - local newer → local canonical (Phase 1 rebuild จะ ship)
#   - prod-only useful → cp → git add
#   - prod-only dead (orphan, no imports) → skip (Phase 1 rebuild drops)
#   - prod backup files → skip
```

## Decision Criteria

| สถานะ | Action |
|-------|--------|
| identical | no action |
| local longer/newer | local canonical |
| prod-only, has callers | cp to local + git add |
| prod-only, no callers (grep) | skip — drop in rebuild |
| prod backup (`*.bak`, `.backup_*`) | skip |
| prod wrong-path config | skip (use correct path) |

## บันทึก decision ทุกอย่างใน RECONCILE_YYYY-MM-DD.md

Document ทุก decision ไม่ว่าจะ commit หรือไม่ — เพื่อ audit trail และ "ทำไม X ถึงไม่อยู่ใน git" สำหรับในอนาคต

## Related

- `RECONCILE_2026-05-17.md` — decision log สำหรับ thai-legal-rag
- `[[local-first-prod-runtime-only]]` — feedback memory: prod = runtime only
- `[[prod-local-src-drift]]` — drift ที่ trigger pattern นี้
