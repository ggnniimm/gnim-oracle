# Qdrant on Server = Docker Network IP, Not localhost

**Date**: 2026-04-18
**Repo**: gnim-oracle-qdrant / thai-legal-rag

## Pattern

Qdrant runs inside Docker on the server. Its port is NOT published to the host, so `localhost:6333` on the server doesn't work.

Must use container IP instead:

```bash
# Get container IP
ssh root@31.97.188.155 "docker inspect thai-legal-rag-qdrant-1 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'"
# → 172.22.0.2

# SSH tunnel to container IP (NOT localhost)
ssh -f -N -L 6334:172.22.0.2:6333 root@31.97.188.155
```

Then use `QDRANT_URL=http://localhost:6334` locally.

## Why

Docker Compose network isolates containers. Qdrant's port is only accessible within the Docker network (e.g., `http://qdrant:6333` from the app container), not from the host's localhost.

## Applied

When running "server eval": eval code runs locally but queries server Qdrant via this tunnel.
Terminology: "eval local → Qdrant server" (not "server eval" which implies eval code runs on server).
