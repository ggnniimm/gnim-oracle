---
date: 2026-05-17
tags: [github-actions, ci-cd, ssh, docker, ghcr, workflow]
project: thai-legal-rag
---

# GitHub Actions: Path + SSH Action Gotchas

## Pattern 1: Workflows ต้องอยู่ที่ repo root เสมอ

GitHub Actions อ่าน workflows จาก `{repo_root}/.github/workflows/` เท่านั้น — ไม่ใช่จาก subdirectory

```bash
# ❌ ผิด — GitHub Actions ไม่เห็น
gnim-oracle/ψ/lab/thai-legal-rag/.github/workflows/build.yml

# ✅ ถูก — GitHub Actions เห็น
gnim-oracle/.github/workflows/build.yml
```

**เวลาสร้าง workflows สำหรับ subproject ใน mono-repo:**
- สร้างไฟล์ที่ repo root `{repo_root}/.github/workflows/`
- `context:` ใน `docker/build-push-action` ชี้ไปที่ subproject path ได้ (e.g., `context: ψ/lab/thai-legal-rag`)
- `paths:` trigger ก็ใช้ subproject path ได้ (e.g., `paths: ["ψ/lab/thai-legal-rag/src/**"]`)

## Pattern 2: ตรวจ action inputs ก่อนใช้เสมอ

`appleboy/ssh-action@v1.0.3` ไม่มี `known_hosts` parameter — มีแค่ `fingerprint`:

```yaml
# ❌ ผิด — known_hosts ไม่ใช่ valid input
- uses: appleboy/ssh-action@v1.0.3
  with:
    host: ${{ secrets.PROD_HOST }}
    key: ${{ secrets.SSH_PRIVATE_KEY }}
    known_hosts: ${{ secrets.SSH_KNOWN_HOSTS }}  # ← ignored silently!

# ✅ ถูก — ใช้ fingerprint
- uses: appleboy/ssh-action@v1.0.3
  with:
    host: ${{ secrets.PROD_HOST }}
    key: ${{ secrets.SSH_PRIVATE_KEY }}
    fingerprint: ${{ secrets.SSH_FINGERPRINT }}  # SHA256:... จาก ssh-keyscan
```

**หา fingerprint:**
```bash
ssh-keyscan -t ed25519 <hostname> 2>/dev/null | ssh-keygen -lf - | awk '{print $2}'
# Output: SHA256:xxxxxxxxxxxx
```

## Pattern 3: ghcr.io public repo = no PAT needed สำหรับ pull

ถ้า GitHub repo เป็น PUBLIC → ghcr.io packages ก็ accessible publicly → prod pull ได้โดยไม่ต้อง `docker login`

```yaml
# CI ต้อง login เพื่อ push
- uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

# Prod pull ไม่ต้อง login (public package)
docker pull ghcr.io/ggnniimm/thai-legal-rag-app:latest
```

## Pattern 4: Registry cache = CI speed สำหรับ heavy dependencies

ถ้า image มี Python packages หนัก (PyTorch, etc.) buildx registry cache ช่วยมาก:

```yaml
cache-from: type=registry,ref=ghcr.io/user/app:cache
cache-to: type=registry,ref=ghcr.io/user/app:cache,mode=max
```

Cache เก็บอยู่ใน registry เอง — ไม่ reset ระหว่าง runs เหมือน local runner cache

## Pattern 5: Deploy via pull vs scp — ความแตกต่างสำคัญ

| Method | เวลา | เมื่อใช้ |
|--------|------|---------|
| `docker pull` จาก registry | ~23s | มี registry — default |
| `docker save \| scp \| docker load` | ~15 นาที (3GB) | fallback ไม่มี internet |

## Related

- `[[docker-platform-and-network-assumptions]]` — ARM64 vs AMD64 + Qdrant internal network
- `[[local-first-prod-runtime-only]]` — prod = runtime only
- `DEPLOY.md` — workflow doc + golden rules
