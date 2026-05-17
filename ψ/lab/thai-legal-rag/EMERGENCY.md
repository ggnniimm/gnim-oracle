# Emergency Procedures — thai-legal-rag

> ใช้เฉพาะเมื่อ prod พัง + ต้องการ fix ด่วน ที่รอ CI build ไม่ได้
> ทุกอย่างที่ทำใน EMERGENCY ต้อง reconcile กลับเข้า git ทันทีหลัง prod stable

---

## 1. ตรวจ prod ก่อน — อะไรพัง?

```bash
# App log
ssh root@31.97.188.155 'docker logs thai-legal-rag-app-1 --tail 50'

# Container status
ssh root@31.97.188.155 'docker ps -a | grep thai-legal-rag'

# Qdrant health
ssh root@31.97.188.155 "docker exec thai-legal-rag-qdrant-1 curl -s http://localhost:6333/healthz"

# External smoke test
bash scripts/prod_smoke.sh
```

---

## 2. App ไม่ start (code error)

### Option A: Rollback image (เร็วที่สุด, recommended)

```bash
# ดู images ที่มีบน prod
ssh root@31.97.188.155 'docker images thai-legal-rag-app'
ssh root@31.97.188.155 'docker images ghcr.io/ggnniimm/thai-legal-rag-app'

# Rollback ไป image ก่อนหน้า (prod pull จาก ghcr.io)
bash scripts/deploy_image.sh ghcr.io/ggnniimm/thai-legal-rag-app:sha-PREVIOUS_SHA

# หรือถ้า image ยังอยู่บน prod
ssh root@31.97.188.155 "cd /app/thai-legal-rag && docker tag thai-legal-rag-app:PREVIOUS_TAG thai-legal-rag-app:latest && docker compose up -d app"
```

### Option B: Hotfix แล้ว push (ถ้า rollback ไม่ได้)

```bash
# แก้ code ที่ local → commit → push to main → รอ CI build (~5 นาที) → deploy
git add <files>
git commit -m "hotfix: <description>"
git push origin main
# รอ GitHub Actions build เสร็จ
gh run watch -R ggnniimm/gnim-oracle  # ดู progress
# Deploy ผ่าน GitHub Actions UI หรือ:
gh workflow run deploy-image.yml -R ggnniimm/gnim-oracle -f image_tag=latest
```

### Option C: Emergency native build บน prod (last resort)

> ⚠️ ใช้เฉพาะเมื่อ internet บน prod ใช้ไม่ได้ / CI ใช้ไม่ได้
> ต้อง reconcile code กลับ git หลัง prod stable

```bash
# Push latest source to prod
rsync -avz --exclude='.git' --exclude='data/' --exclude='ψ/' --exclude='__pycache__' \
  . root@31.97.188.155:/app/thai-legal-rag/

# Build บน prod (native amd64, ใช้ layer cache)
ssh root@31.97.188.155 'cd /app/thai-legal-rag && docker build -t thai-legal-rag-app:emergency-$(date +%Y%m%d-%H%M) -t thai-legal-rag-app:latest .'

# Restart
ssh root@31.97.188.155 'cd /app/thai-legal-rag && docker compose up -d app'

# Verify
bash scripts/prod_smoke.sh
```

---

## 3. Qdrant data หาย / chunk count ผิด

```bash
# ตรวจ chunk count ก่อน
ssh root@31.97.188.155 "docker exec thai-legal-rag-app-1 python3 -c \"
import urllib.request, json
r = urllib.request.urlopen('http://qdrant:6333/collections/thai_legal_rag')
print('Chunks:', json.load(r)['result']['points_count'])
\""

# Restore จาก latest local snapshot
bash scripts/deploy_data.sh
# (script จะ export local → scp → restore → verify)

# ถ้า local Qdrant ก็พัง → restore จาก snapshot file
bash scripts/snapshot_restore.sh data/snapshots/SNAPSHOT_FILE.snapshot
bash scripts/deploy_data.sh data/snapshots/SNAPSHOT_FILE.snapshot
```

Latest known-good snapshot: `data/snapshots/thai_legal_rag-336578599102351-2026-05-17-05-19-13.snapshot`

---

## 4. prod compose พัง (Traefik / network issue)

```bash
# ดู compose status
ssh root@31.97.188.155 'cd /app/thai-legal-rag && docker compose ps'

# Full restart
ssh root@31.97.188.155 'cd /app/thai-legal-rag && docker compose down && docker compose up -d'

# ถ้า Traefik มีปัญหา
ssh root@31.97.188.155 'docker restart traefik'
```

---

## 5. หลัง Emergency — Reconcile กลับ git

ทุกอย่างที่แก้บน prod ด้วยมือต้องเข้า git ภายใน session เดียวกัน:

```bash
# ถ้าแก้ code บน prod โดยตรง
bash scripts/drift_check.sh  # ดูว่า drift อยู่ที่ไหน
# แก้ local ให้ตรงกับที่แก้บน prod
# commit + push + CI build + deploy image ปกติ

# บันทึก DEPLOY_LOG.md
echo "$(date '+%Y-%m-%d %H:%M') EMERGENCY: <description of what happened>" >> DEPLOY_LOG.md
```

---

## What NOT to do in Emergency

- ❌ อย่า `docker exec app-container python3 pipeline/...` — drift กลับมา
- ❌ อย่า `docker cp file container:/app/src/...` แล้วลืม commit
- ❌ อย่า `git push --force` เด็ดขาด
- ❌ อย่า edit code บน prod โดยตรงโดยไม่ reconcile

---

## Contacts / References

- Prod: `root@31.97.188.155`
- App container: `thai-legal-rag-app-1`
- Qdrant container: `thai-legal-rag-qdrant-1`
- Prod URL: https://mwaprocure.gnim.cloud
- ghcr.io: `ghcr.io/ggnniimm/thai-legal-rag-app`
- GitHub Actions: https://github.com/ggnniimm/gnim-oracle/actions
