---
date: 2026-05-17
tags: [docker, deploy, platform, network, local-first]
project: thai-legal-rag
---

# Docker Deploy: Platform + Network Assumptions ที่พลาดได้ง่าย

## Pattern 1: Always specify `--platform linux/amd64` เมื่อ build บน Mac M-chip

Mac M1/M2/M3 (ARM64) → Linux VPS (x86_64/AMD64) คือ combination ที่พบบ่อยมาก แต่ถ้าไม่ระบุ platform Docker จะ build ให้ host (ARM64) ซึ่งรันบน AMD64 prod ไม่ได้ → `exec format error`

```bash
# ❌ พัง
docker build -t my-app:latest .

# ✅ ถูก
docker build --platform linux/amd64 -t my-app:latest .
```

**เพิ่ม --platform linux/amd64 เป็น default ใน build script เสมอ** สำหรับ project ที่ prod เป็น Linux x86_64

## Pattern 2: Verify Docker network topology ก่อนเขียน script

ถ้า service อยู่ใน internal Docker network (ไม่ expose port ออก host) ต้องเข้าถึงผ่าน container อื่นที่อยู่ใน network เดียวกัน — ไม่ใช่ผ่าน `localhost:PORT` บน host

```bash
# ❌ ใช้ไม่ได้ถ้า Qdrant ไม่ expose port
ssh prod 'curl http://localhost:6333/collections/...'

# ✅ ผ่าน app container ที่อยู่ใน internal network เดียวกับ Qdrant
ssh prod 'docker exec app-container python3 -c "urllib.request.urlopen(\"http://qdrant:6333/...\")"'
```

**ตรวจ `ports:` ใน docker-compose ก่อนเขียน script** ที่ต้องเรียก service บน prod

## Pattern 3: Image ควรมีเฉพาะ runtime code — ไม่ใช่ build tools

ถ้า project ใช้ local-first model (OCR/index/eval รันที่ local) image ที่ deploy ไป prod ควรมีแค่:
- `src/` — core business logic
- `app/` — UI/API

ไม่ควรมี `pipeline/` (OCR scripts, indexers, eval tools) แม้จะ "เผื่อไว้ debug" เพราะ:
1. เพิ่มขนาด image โดยไม่จำเป็น
2. เปิดช่อง temptation ว่าจะรัน pipeline บน prod → drift กลับมาอีก
3. ขัดกับ principle ที่ตั้งไว้

## Qdrant snapshot restore บน prod (internal network)

```bash
# 1. mkdir ใน Qdrant container
docker exec qdrant-container mkdir -p /qdrant/snapshots/collection_name

# 2. copy snapshot เข้า container
docker cp snapshot.file qdrant-container:/qdrant/snapshots/collection_name/

# 3. trigger restore ผ่าน app container (ที่ reach qdrant:6333 ได้)
docker exec app-container python3 -c "
import urllib.request, json
location = 'file:///qdrant/snapshots/collection_name/snapshot.file'
url = 'http://qdrant:6333/collections/collection_name/snapshots/recover'
payload = json.dumps({'location': location, 'priority': 'snapshot'}).encode()
req = urllib.request.Request(url, data=payload, method='PUT',
  headers={'Content-Type': 'application/json'})
print(json.load(urllib.request.urlopen(req)))
"
```

## Related

- `[[local-first-prod-runtime-only]]` — prod = runtime only; pipeline stays local
- `[[reconcile-before-rebuild]]` — snapshot prod ก่อน switch architecture
- `DEPLOY.md` — golden rules + full workflow
