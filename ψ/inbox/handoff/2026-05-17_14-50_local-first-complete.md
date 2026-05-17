# Handoff: Local-first Architecture Complete (Phase 0→3)

**Date**: 2026-05-17 14:50
**Context**: 95%

📡 Session: a3832748 | thai-legal-rag | ~8h (Phase 0 เช้า → Phase 3 บ่าย)

## What We Did

**Phase 0 — Reconcile**
- Snapshot prod `/app/` → diff → commit stranded files (run_eval.py, build_bm25_index.py, patch_metadata.py, golden_test_cases.json backups) เข้า git
- เขียน `RECONCILE_2026-05-17.md` (decision log)

**Phase 1 — Local-first Build + Deploy**
- สร้าง `scripts/build.sh` (--platform linux/amd64), `deploy_image.sh`, `deploy_data.sh`, `snapshot_export.sh`, `snapshot_restore.sh`
- สร้าง `docker-compose.prod.yml` (prod-only, ไม่มี pipeline mount)
- Fixed Dockerfile: ลบ `COPY pipeline/` ออก (prod = runtime only)
- Fixed deploy_data.sh: Qdrant internal network → ผ่าน app container
- Manual deploy สำเร็จ: HTTP 200, 31,927 chunks ✓

**Phase 2+C — GitHub Actions + ghcr.io**
- `.github/workflows/build-image.yml`: push main → buildx amd64 → ghcr.io (5m13s)
- `.github/workflows/deploy-image.yml`: manual dispatch → SSH pull → compose up (23s)
- GitHub Secrets: PROD_HOST, SSH_PRIVATE_KEY, SSH_FINGERPRINT
- First CI build + deploy verified ✓

**Phase 3 — Guardrails**
- `scripts/drift_check.sh`: 8 files local vs prod (PASS verified)
- `scripts/prod_smoke.sh`: 4-check health (HTTP, container, Qdrant chunks)
- `EMERGENCY.md`: rollback A/B/C + Qdrant restore procedures
- `DEPLOY.md`: อัปเดต GitHub Actions paths + drift check section
- Pre-commit hook (advisory)

**Docs + Cleanup**
- `PLAYBOOK.md`: คู่มือการทำงาน 5 scenarios
- ลบ empty dirs ใน md_backup (14 dirs), ย้าย 11 subdirs ไป md_removed

## Pending

- [ ] รัน local eval `eval/run_eval.py` เมื่อ Vertex quota ว่าง (verify 31,927 = 82/84)
- [ ] Monitor TC-067/074 ก่อน fix
- [ ] ทดสอบ second CI build — verify registry cache เร็วกว่า 5m13s
- [ ] เริ่ม log DEPLOY_LOG.md ทุก deploy จากนี้
- [ ] Issues #31-35 (cleanup dead imports, OCR schema, ว139 mismatch, eval gate, prod backups)
- [ ] PLAYBOOK.md markdown lint warnings (blanks around fences/lists, code block language)

## Next Session

- [ ] รัน eval local ยืนยัน baseline 82/84 บน 31,927 chunks
- [ ] ถ้า eval PASS → prod ถือว่า stable ไม่ต้องทำอะไรเพิ่ม
- [ ] ถ้า eval ต่ำกว่า 82 → investigate TC ที่ fail เพิ่มใหม่
- [ ] พิจารณา issues #31-35 ว่าอันไหนทำก่อน

## Key Files

- `PLAYBOOK.md` — คู่มือการทำงาน (ใหม่)
- `DEPLOY.md` — deploy workflow
- `EMERGENCY.md` — rollback procedures (ใหม่)
- `scripts/drift_check.sh` — ใช้ start of session
- `scripts/prod_smoke.sh` — health check
- `.github/workflows/build-image.yml` — CI build
- `.github/workflows/deploy-image.yml` — CI deploy

## Prod State

| ข้อมูล | ค่า |
|--------|-----|
| Chunks | 31,927 |
| Eval baseline | 82/84 (2026-05-16) |
| Image | ghcr.io/ggnniimm/thai-legal-rag-app:latest (sha-1dec2fe) |
| HTTP | 200 ✓ |
| Drift | 0 (drift_check PASS) |
