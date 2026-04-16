---
title: ## Docker Qdrant Server Mode and Embedded Mode Limits
tags: [docker, qdrant, deployment, thai-legal-rag, infrastructure]
created: 2026-04-14
source: Oracle Learn
---

# ## Docker Qdrant Server Mode and Embedded Mode Limits

## Docker Qdrant Server Mode and Embedded Mode Limits

### Context
Thai Legal RAG — Docker deployment with Qdrant (2026-03-24).

### Pattern: Qdrant Embedded Mode Is Impractical in Docker at Scale
28K+ points → 5+ GB RAM, long startup, single-process lock. Use Qdrant server container for production:
```yaml
services:
  qdrant:
    image: qdrant/qdrant
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
  app:
    environment:
      - QDRANT_URL=http://qdrant:6333  # internal network
```

### Pattern: Docker env_file Overridden by environment Section
`.env` contains `QDRANT_URL=http://localhost:6333`. To override to empty in container:
```yaml
environment:
  - QDRANT_URL=  # empty string overrides env_file value
```
`environment` takes precedence over `env_file`. But empty string `""` is falsy in Python — check your config logic.

### Pattern: Check .env Contents Before Docker Troubleshooting
`grep QDRANT .env` takes 2 seconds. Not checking it first can waste 30+ minutes debugging connection errors that are just env var conflicts.

### Pattern: Qdrant Re-index Cost
~29K chunks via Gemini embedding API takes ~45 min. Qdrant server volume (`qdrant_data`) persists across container restarts — this is a one-time cost. Don't clear dedup.db unless switching backends.

### Pattern: Docker `restart app` Does Not Update Code
`docker compose restart` reuses cached image. Always `docker compose build app && docker compose up -d app` after code changes.

---
*Added via Oracle Learn*
