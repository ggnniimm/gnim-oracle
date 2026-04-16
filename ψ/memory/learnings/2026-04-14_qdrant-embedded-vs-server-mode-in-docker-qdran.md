---
title: ## Qdrant Embedded vs Server Mode in Docker
tags: [qdrant, docker, embedded-mode, server-mode, memory]
created: 2026-04-14
source: Thai Legal RAG Docker deployment 2026-03-24
---

# ## Qdrant Embedded vs Server Mode in Docker

## Qdrant Embedded vs Server Mode in Docker

Qdrant embedded mode (`QdrantClient(path=...)`) loads the entire index into app process memory. For 28K+ points, this consumes 5+ GB RAM and causes long startup delays — impractical inside a Docker container with 8GB limit.

**How to apply**: For collections >10K points in Docker, always use Qdrant server mode (separate container). Set `QDRANT_URL=http://qdrant:6333` in app's environment. Re-index from host using `QDRANT_URL=http://localhost:6333`. The server manages its own memory efficiently and starts instantly.

**Docker-compose note**: `env_file` values are overridden by `environment` section — use this to override `QDRANT_URL` from shared .env files.

qdrant_client itself warns at 20K points about embedded mode performance.

---
*Added via Oracle Learn*
