# Deploy Guide — thai-legal-rag

## Golden Rules (Local-first model)

| Do | Don't |
|----|-------|
| ✅ OCR → local | ❌ ssh prod + run index/eval/OCR |
| ✅ Index → local Qdrant | ❌ docker cp + docker commit (ยกเว้น emergency) |
| ✅ Eval → local | ❌ docker exec ... run_eval.py บน prod |
| ✅ Push image + snapshot → prod | ❌ Edit code directly on prod |
| ✅ Prod = pull + serve เท่านั้น | |

---

## Prerequisites

- Docker Desktop running locally
- SSH access: `ssh root@31.97.188.155` (port 22, อาจต้อง hotspot ถ้า ISP block)
- Local Qdrant healthy: `curl http://localhost:6333/`
- GCP credentials active: `gcloud auth application-default print-access-token`

---

## Code Deploy (image เปลี่ยน)

ใช้เมื่อ: แก้ `src/`, `app/`, `pipeline/`, `requirements.txt`

```bash
# 1. Build + tag
bash scripts/build.sh
# จะ print: VERSION_TAG=thai-legal-rag-app:v20260517-1205-3c0f72a

# 2. (optional) Run local smoke test
docker compose up -d app
curl http://localhost:8501/healthz

# 3. Deploy to prod
bash scripts/deploy_image.sh thai-legal-rag-app:v20260517-1205-3c0f72a
# Script: docker save → scp → docker load → docker compose up -d app → smoke test

# 4. Log the deploy
echo "$(date '+%Y-%m-%d %H:%M') deploy_image $VERSION_TAG" >> DEPLOY_LOG.md
```

---

## Data Deploy (Qdrant เปลี่ยน — หลัง reindex)

ใช้เมื่อ: เพิ่ม/แก้ MDs ใน `data/md_backup/` แล้ว reindex ที่ local

```bash
# 1. Verify local chunk count
curl -s http://localhost:6333/collections/thai_legal_rag | python3 -c \
  "import json,sys; print('Chunks:', json.load(sys.stdin)['result']['points_count'])"

# 2. Run local eval (ยืนยัน 82/84 ก่อน deploy)
# python3 eval/run_eval.py  # (รอ quota ว่างก่อน)

# 3. Export snapshot + deploy to prod
bash scripts/deploy_data.sh
# Script: snapshot_export → scp → Qdrant upload → verify count match

# 4. Log
echo "$(date '+%Y-%m-%d %H:%M') deploy_data chunks=$(curl -s http://localhost:6333/collections/thai_legal_rag | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"result\"][\"points_count\"])')" >> DEPLOY_LOG.md
```

---

## Full Deploy (code + data พร้อมกัน)

```bash
# ลำดับสำคัญ: image ก่อน, data ทีหลัง
bash scripts/build.sh
bash scripts/deploy_image.sh <VERSION_TAG>
bash scripts/deploy_data.sh
```

---

## Update Prod docker-compose.yml (ครั้งแรก / เมื่อ config เปลี่ยน)

```bash
# Push updated compose file to prod
scp docker-compose.prod.yml root@31.97.188.155:/app/thai-legal-rag/docker-compose.yml
ssh root@31.97.188.155 'cd /app/thai-legal-rag && docker compose up -d'
```

---

## Pin Qdrant Version

ทั้ง local และ prod ใช้ `qdrant/qdrant:v1.17.1` (pinned 2026-05-17)

ถ้า upgrade Qdrant:
1. `bash scripts/snapshot_export.sh` (backup ก่อนเสมอ)
2. แก้ version ใน `docker-compose.yml` (local + prod)
3. `docker compose pull qdrant && docker compose up -d qdrant`
4. ตรวจ chunk count ยังเท่าเดิม
5. Update `DEPLOY.md` ด้วย version ใหม่

---

## Rollback

### Rollback image

```bash
# ดู image ที่มีอยู่
docker images thai-legal-rag-app

# Load image เก่าขึ้น prod
bash scripts/deploy_image.sh thai-legal-rag-app:vPREVIOUS_TAG
```

Current rollback target: `patched-2026-05-16-inactive-filter`

### Rollback Qdrant data

```bash
# Restore snapshot เก่า (local)
bash scripts/snapshot_restore.sh data/snapshots/SNAPSHOT_FILE.snapshot

# Restore snapshot เก่า (prod)
bash scripts/snapshot_restore.sh data/snapshots/SNAPSHOT_FILE.snapshot prod
```

Latest local snapshot: `data/snapshots/thai_legal_rag-336578599102351-2026-05-17-05-19-13.snapshot`

---

## Monitoring

```bash
# Prod logs
ssh root@31.97.188.155 'docker logs thai-legal-rag-app-1 --tail 50 -f'

# Prod Qdrant chunk count
ssh root@31.97.188.155 "curl -s 'http://localhost:6333/collections/thai_legal_rag'" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['result']['points_count'])"

# Prod app health
curl -s https://mwaprocure.gnim.cloud/healthz
```

---

## Emergency (อย่าใช้ถ้าไม่จำเป็น)

ถ้า prod พังและต้องแก้ urgent — ดู `EMERGENCY.md` (Phase 3)
