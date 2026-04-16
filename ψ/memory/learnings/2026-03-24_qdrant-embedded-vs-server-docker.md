---
name: qdrant-embedded-vs-server-docker
description: Qdrant embedded mode uses 5+ GB RAM for 28K points in Docker — use server container instead for production
type: feedback
---

# Qdrant Embedded vs Server Mode in Docker

Qdrant embedded mode (QdrantClient(path=...)) loads the entire index into the app process memory. For 28K+ points, this consumes 5+ GB RAM and causes long startup delays — impractical inside a Docker container.

**Why:** Docker containers typically have less RAM than the host. Embedded mode that works fine on Mac (16/32GB) will hang or OOM inside a container with 8GB limit. The qdrant_client itself warns at 20K points.

**How to apply:** For collections >10K points in Docker, always use Qdrant server mode (separate container). Set `QDRANT_URL=http://qdrant:6333` in app's environment. Re-index via server API from host using `QDRANT_URL=http://localhost:6333`. The server manages its own memory efficiently and starts instantly. Remember that `env_file` values are overridden by `environment` section in docker-compose — use this to override `QDRANT_URL` from shared .env files.
