---
date: 2026-05-17
tags: [guardrails, drift-check, deploy, devops, local-first, pre-commit]
project: thai-legal-rag
---

# Guardrails Design Pattern สำหรับ Local-first Deploy

## Pattern 1: drift_check.sh — ตรวจ prod vs local ก่อน reindex

เมื่อ prod code drift จาก local แบบ silent (เช่น emergency docker cp) ต้องมี tool ตรวจ:

```bash
# Key files to check (ไม่ต้องทุกไฟล์ — เฉพาะ "most likely to drift")
WATCH_FILES=(
  "src/config.py"
  "src/ingestion/md_loader.py"
  "src/retrieval/reranker.py"
  # ...
)

# Pull จาก prod container แล้ว diff
PROD_CONTENT=$(ssh prod "docker exec app-container cat /app/$FILE")
diff <(echo "$LOCAL_CONTENT") <(echo "$PROD_CONTENT")
```

**รันเมื่อ**: start of session, ก่อน reindex, หลัง emergency

## Pattern 2: prod_smoke.sh — multi-layer health check

smoke test ที่ดีต้องตรวจ layers ต่างกัน:

| Check | ทำไม |
|-------|------|
| External HTTP (curl domain) | ตรวจ Traefik + TLS + DNS ด้วย |
| Internal HTTP (curl localhost) | isolate network issue |
| Container status (docker inspect) | ตรวจว่า process ไม่ crash-looping |
| Data layer (Qdrant chunk count) | ตรวจว่า data ยัง intact |

## Pattern 3: EMERGENCY.md — 3-level rollback ตาม speed vs drift-risk

| Level | วิธี | เวลา | Drift Risk |
|-------|------|------|-----------|
| A (preferred) | `docker pull` image ก่อนหน้าจาก registry | ~23s | 0 |
| B (standard) | hotfix commit → CI build → deploy | ~5-10 นาที | 0 |
| C (last resort) | native build บน prod | ~5 นาที | สูง (ต้อง reconcile) |

เรียง A→C ตาม "drift risk ต่ำ → สูง" ไม่ใช่ตาม "เร็ว → ช้า" เพราะ Option A เร็วที่สุดด้วย

## Pattern 4: Pre-commit hook — advisory, non-blocking

Hook ที่ block commit ทำให้ workflow ช้าเกินไปถ้า trigger บ่อย ใช้ advisory pattern:

```bash
# ✅ advisory — exit 0 เสมอ, แค่ print warning
if changed_files_touch_src; then
  echo "⚠️ Remember to deploy after push"
fi
exit 0

# ❌ blocking — exit 1 ถ้า drift detected (น่ารำคาญมากสำหรับ commits ที่ไม่เกี่ยวกับ deploy)
```

## Pattern 5: Pre-commit hooks ใน mono-repo ไม่อยู่ใน version control

`.git/hooks/` ไม่ track ใน git ถ้าต้องการ share hook กับ team ให้เก็บใน `scripts/hooks/` แล้วมี setup script:

```bash
# scripts/install-hooks.sh
ln -sf "$(pwd)/scripts/hooks/pre-commit" .git/hooks/pre-commit
```

## Related

- `[[local-first-prod-runtime-only]]` — principle หลักที่ guardrails นี้ enforce
- `[[docker-platform-and-network-assumptions]]` — failure modes ที่ guardrails ป้องกัน
- `EMERGENCY.md` — full rollback procedures
- `DEPLOY.md` — golden rules + workflow
