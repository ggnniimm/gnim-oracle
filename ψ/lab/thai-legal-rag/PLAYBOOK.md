# คู่มือการทำงาน — Thai Legal RAG

> คู่มือนี้ตอบคำถาม "ทำอะไร เมื่อไหร่" สำหรับ 5 scenario หลัก
> รายละเอียด deploy → `DEPLOY.md` | ฉุกเฉิน → `EMERGENCY.md`

---

## สถาปัตยกรรม (Local-first Model)

```
Local machine                                    Prod (31.97.188.155)
─────────────────────────────────────────────    ──────────────────────────────
Google Drive (PDF)
   │ OCR (Gemini Pro)
   ▼
data/md_backup/      ← canonical corpus
   │ pipeline/index_md_folder.py
   ▼
Local Qdrant         ← single source of truth
(31,927 chunks)
   │ eval/run_eval.py
   ▼
82/84 PASS ✓         ← verify ก่อน deploy เสมอ
   │
   ├── docker build → ghcr.io ──────────────────→ docker pull → App container
   │   (GitHub Actions อัตโนมัติ เมื่อ push main)
   │
   └── snapshot_export → scp → restore ─────────→ Qdrant container
       (manual, รันเมื่อ corpus เปลี่ยน)
                                                   │
                                                   ▼
                                             mwaprocure.gnim.cloud
```

**กฎเหล็ก:**
- ❌ ไม่ index บน prod
- ❌ ไม่ eval บน prod
- ❌ ไม่ `docker cp` + แก้โค้ด prod โดยตรง (ยกเว้น EMERGENCY.md)
- ✅ Prod = pull image + restore snapshot + serve เท่านั้น

---

## เริ่ม Session ใหม่

ทำทุกครั้งก่อนเริ่มงาน:

```bash
cd ψ/lab/thai-legal-rag

# 1. ตรวจ local Qdrant ทำงานอยู่
curl -s http://localhost:6333/ | python3 -c "import json,sys; d=json.load(sys.stdin); print('Qdrant OK:', d.get('version','?'))"

# 2. ตรวจ chunk count local
curl -s http://localhost:6333/collections/thai_legal_rag | \
  python3 -c "import json,sys; print('Chunks:', json.load(sys.stdin)['result']['points_count'])"
# ควรเป็น ~31,927

# 3. ตรวจ prod ไม่ drift
bash scripts/drift_check.sh --quiet
# PASS = ปกติ, DRIFT = ต้อง deploy image ใหม่

# 4. ตรวจ prod healthy
bash scripts/prod_smoke.sh
```

ถ้า local Qdrant ไม่ทำงาน:
```bash
docker compose up -d qdrant
```

---

## Scenario 1: มีเอกสารใหม่ / แก้ไขเอกสาร

**เมื่อ**: ได้ PDF ใหม่จาก กรมบัญชีกลาง, ศาลปกครอง, อัยการสูงสุด หรือแก้ MD ที่มีอยู่

### 1a. OCR PDF ใหม่

```bash
# OCR ด้วย Gemini Pro (high quality)
THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/batch_ocr.py \
  --file path/to/document.pdf \
  --output data/md_backup/

# OCR หลายไฟล์
THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/batch_ocr.py \
  --folder path/to/pdfs/ \
  --output data/md_backup/
```

ผล OCR จะบันทึกเป็น `.md` ใน `data/md_backup/`

### 1b. Index เข้า Qdrant

```bash
# Incremental index (skip ไฟล์ที่ index แล้ว)
QDRANT_URL=http://localhost:6333 \
THAI_RAG_DATA_DIR=$(pwd)/data \
python3 pipeline/index_md_folder.py --dir data/md_backup --no-lightrag

# Force re-index ไฟล์เดียว (ถ้าแก้ MD แล้ว)
QDRANT_URL=http://localhost:6333 \
THAI_RAG_DATA_DIR=$(pwd)/data \
python3 pipeline/index_md_folder.py --dir data/md_backup --force-reindex --file ชื่อไฟล์.md
```

ตรวจ chunk count หลัง index:
```bash
curl -s http://localhost:6333/collections/thai_legal_rag | \
  python3 -c "import json,sys; print('Chunks:', json.load(sys.stdin)['result']['points_count'])"
```

### 1c. รัน Eval ยืนยัน

```bash
# Full eval (รอ Vertex quota ว่าง — ใช้เวลา ~30 นาที)
QDRANT_URL=http://localhost:6333 \
THAI_RAG_DATA_DIR=$(pwd)/data \
python3 eval/run_eval.py 2>&1 | tee /tmp/eval_out.txt

# ดูผล
tail -20 /tmp/eval_out.txt
# เป้าหมาย: 82/84 PASS ขึ้นไป
```

ห้ามรัน eval 2 ตัวพร้อมกัน:
```bash
ps aux | grep run_eval  # ตรวจก่อนรัน
```

### 1d. Deploy Data ขึ้น Prod

เมื่อ eval ผ่านแล้ว:
```bash
bash scripts/deploy_data.sh
# Script: snapshot_export → scp → Qdrant restore → verify count match
```

ใช้เวลา ~10-15 นาที (480MB snapshot)

---

## Scenario 2: แก้ Source Code

**เมื่อ**: แก้ `src/`, `app/`, `requirements.txt`

### วิธี A: GitHub Actions (recommended)

```bash
# 1. แก้ code + ทดสอบ local
docker compose up -d  # local app
# เปิด http://localhost:8501 ทดสอบ

# 2. Commit + push
git add src/... app/...
git commit -m "fix: ..."
git push origin main
# → GitHub Actions build อัตโนมัติ (~5 นาที)

# 3. ดู CI progress
gh run list -R ggnniimm/gnim-oracle --workflow=build-image.yml

# 4. Deploy เมื่อ build เสร็จ
gh workflow run deploy-image.yml -R ggnniimm/gnim-oracle -f image_tag=latest
# หรือไปที่ GitHub Actions → Deploy to Production → Run workflow
```

### วิธี B: Local build (ถ้า CI ใช้ไม่ได้)

```bash
bash scripts/build.sh --push
# Print: REMOTE_TAG=ghcr.io/ggnniimm/thai-legal-rag-app:local-...

bash scripts/deploy_image.sh ghcr.io/ggnniimm/thai-legal-rag-app:local-...
```

### ยืนยันหลัง deploy

```bash
bash scripts/prod_smoke.sh
bash scripts/drift_check.sh
```

---

## Scenario 3: แก้ Test Cases (Eval)

**เมื่อ**: เพิ่ม TC ใหม่, แก้ must_contain, แก้ query

ไฟล์: `eval/golden_test_cases.json`

Format:
```json
{
  "id": "TC-085",
  "query": "คำถามภาษาไทย?",
  "must_contain": ["คำหลักที่ต้องมีในคำตอบ"],
  "semantic_check": "ประโยคที่ตรวจด้วย semantic similarity"
}
```

**must_contain tips:**
- ใส่ direction word เสมอ (ไม่ต้องรอ, ไม่อาจ, มีสิทธิ)
- ถ้ามีหลาย alternative: `["ทางเลือก1", "ทางเลือก2"]` (OR logic)
- Array-of-arrays = AND: `[["ต้อง"], ["ภายใน", "ไม่เกิน"]]`

รัน TC เดี่ยวเพื่อ debug:
```bash
QDRANT_URL=http://localhost:6333 \
THAI_RAG_DATA_DIR=$(pwd)/data \
python3 eval/run_eval.py --id TC-085 -v
```

รัน 2-3 รอบ ถ้า inconsistent = LLM variance (แก้ must_contain ให้ยืดหยุ่นขึ้น)

---

## Scenario 4: ตรวจคุณภาพ Prod

**รัน weekly หรือหลัง deploy ทุกครั้ง:**

```bash
# Health + chunk count
bash scripts/prod_smoke.sh

# Drift check
bash scripts/drift_check.sh

# Prod logs (ถ้าสงสัยมี error)
ssh root@31.97.188.155 'docker logs thai-legal-rag-app-1 --tail 50'

# Prod chunk count โดยตรง
ssh root@31.97.188.155 "docker exec thai-legal-rag-app-1 python3 -c \"
import urllib.request, json
r = urllib.request.urlopen('http://qdrant:6333/collections/thai_legal_rag')
print(json.load(r)['result']['points_count'])
\""
```

**ค่า baseline ปัจจุบัน:**
- Chunks: 31,927
- Eval: 82/84 PASS
- HTTP: 200

---

## Scenario 5: Prod พัง — ฉุกเฉิน

ดู `EMERGENCY.md` สำหรับ step-by-step

ขั้นตอนสั้น:
```bash
# 1. ตรวจ
bash scripts/prod_smoke.sh
ssh root@31.97.188.155 'docker logs thai-legal-rag-app-1 --tail 30'

# 2. Rollback image (เร็วที่สุด)
ssh root@31.97.188.155 'docker images ghcr.io/ggnniimm/thai-legal-rag-app'
bash scripts/deploy_image.sh ghcr.io/ggnniimm/thai-legal-rag-app:sha-PREVIOUS

# 3. ถ้า data หาย
bash scripts/deploy_data.sh
```

---

## Scripts Reference

| Script | ทำอะไร | ใช้เมื่อ |
|--------|--------|---------|
| `scripts/drift_check.sh` | diff 8 key src/ files local vs prod | start of session, ก่อน reindex |
| `scripts/prod_smoke.sh` | 4-check health (HTTP, container, chunks) | ก่อน+หลัง deploy |
| `scripts/build.sh` | build docker image linux/amd64 | local fallback |
| `scripts/build.sh --push` | build + push ไป ghcr.io | local fallback |
| `scripts/deploy_image.sh <tag>` | deploy image ไป prod (pull จาก registry) | หลัง CI build |
| `scripts/deploy_image.sh --local <tag>` | deploy image ไป prod (scp) | ไม่มี registry |
| `scripts/deploy_data.sh` | export snapshot → deploy ไป prod | หลัง reindex |
| `scripts/snapshot_export.sh` | export Qdrant snapshot เป็นไฟล์ | backup ก่อน ops |
| `scripts/snapshot_restore.sh <file>` | restore snapshot ไป local Qdrant | recovery |

---

## GitHub Actions

| Workflow | Trigger | ทำอะไร |
|----------|---------|--------|
| `build-image.yml` | push to main (src/, app/, Dockerfile) | build linux/amd64 → push ghcr.io |
| `deploy-image.yml` | manual dispatch | SSH → docker pull → compose up → smoke test |

```bash
# Trigger deploy manually
gh workflow run deploy-image.yml -R ggnniimm/gnim-oracle -f image_tag=latest

# ดู runs
gh run list -R ggnniimm/gnim-oracle --limit=5
```

---

## Environment

| ตัวแปร | ค่า | ใช้ที่ |
|--------|-----|-------|
| `QDRANT_URL` | `http://localhost:6333` | pipeline, eval (local) |
| `QDRANT_URL` | `http://qdrant:6333` | app container บน Docker |
| `THAI_RAG_DATA_DIR` | `$(pwd)/data` | pipeline, eval |
| `GOOGLE_CLOUD_PROJECT` | `gen-lang-client-0136329629` | Vertex AI mode |
| `GOOGLE_CLOUD_LOCATION` | `global` | embedding (gemini-embedding-2) |
| `EMBEDDING_MODEL` | `gemini-embedding-2` | indexing |

Vertex AI auth (local):
```bash
gcloud auth application-default login  # ใช้ mwadct@gmail.com
# Credentials: ~/.config/gcloud/application_default_credentials.json
```

---

## Key Facts

| ข้อมูล | ค่า |
|--------|-----|
| Prod URL | https://mwaprocure.gnim.cloud |
| Prod server | root@31.97.188.155 |
| App container | thai-legal-rag-app-1 |
| Qdrant container | thai-legal-rag-qdrant-1 |
| Qdrant version | v1.17.1 (pinned ทั้ง local + prod) |
| Embedding model | gemini-embedding-2 (location: global, dim: 3072) |
| Generator | gemini-2.5-flash (date-calc → gemini-2.5-pro) |
| Corpus canonical | `data/md_backup/` — 1,387 MDs |
| Prod chunks baseline | 31,927 |
| Eval baseline | 82/84 PASS (2026-05-16) |
| Registry | ghcr.io/ggnniimm/thai-legal-rag-app |

---

## Troubleshooting

**Local Qdrant ไม่ start:**
```bash
docker compose up -d qdrant
docker logs thai-legal-rag-qdrant-1 --tail 20
```

**Index ช้ามาก / หยุด:**
```bash
# ตรวจว่าไม่มี index อื่นรันอยู่
ps aux | grep index_md_folder
# ตรวจ Vertex quota (embedding ใช้ global quota)
```

**Eval ผล inconsistent:**
- รัน TC เดี่ยว 3 ครั้ง: ถ้า inconsistent = LLM variance
- แก้ `must_contain` ให้มี alternatives มากขึ้น
- ห้ามรัน eval 2 ตัวพร้อมกัน

**SSH ไม่ได้ port 22:**
```bash
# ใช้ hotspot (ISP บางเจ้า block port 22)
# หรือตรวจ ssh.socket บน VPS
```

**prod ไม่ response HTTP 200:**
```bash
ssh root@31.97.188.155 'docker logs thai-legal-rag-app-1 --tail 30'
ssh root@31.97.188.155 'docker ps -a | grep thai-legal-rag'
# ดู EMERGENCY.md ถ้าแก้ไม่ได้
```

**Qdrant chunk count ต่ำกว่า baseline:**
```bash
# ตรวจว่า inactive filter ทำงานถูกต้องหรือ data หาย
ssh root@31.97.188.155 "docker exec thai-legal-rag-app-1 python3 -c \"
import urllib.request, json
r = urllib.request.urlopen('http://qdrant:6333/collections/thai_legal_rag')
d = json.load(r)['result']
print('points:', d['points_count'])
print('status:', d['status'])
\""
# ถ้าหายจริง → bash scripts/deploy_data.sh
```
