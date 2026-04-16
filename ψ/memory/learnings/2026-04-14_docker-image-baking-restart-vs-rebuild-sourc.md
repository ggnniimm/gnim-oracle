---
title: ## Docker Image Baking — Restart vs Rebuild
tags: [docker, image-baking, deployment, code-changes]
created: 2026-04-14
source: Thai Legal RAG Docker deployment 2026-03-28
---

# ## Docker Image Baking — Restart vs Rebuild

## Docker Image Baking — Restart vs Rebuild

Source code is baked into Docker image at build time. `docker compose restart` only restarts the container using the existing image — it does NOT pick up code changes.

**How to apply**: After any code change to `app/` or `src/`, always run:
```bash
docker compose build app && docker compose up -d app
```
Never just `restart` when you've changed source files. `restart` only works for config changes that affect the running container (env vars, etc.).

---
*Added via Oracle Learn*
