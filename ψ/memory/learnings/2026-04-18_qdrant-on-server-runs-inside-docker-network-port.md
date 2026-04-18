---
title: Qdrant on server runs inside Docker network — port NOT published to host localho
tags: [qdrant, docker, ssh-tunnel, eval, thai-legal-rag]
created: 2026-04-18
source: rrr: gnim-oracle-qdrant 2026-04-18
project: github.com/ggnniimm/gnim-oracle
---

# Qdrant on server runs inside Docker network — port NOT published to host localho

Qdrant on server runs inside Docker network — port NOT published to host localhost. Must SSH tunnel to container IP directly:

```bash
# Get IP
docker inspect thai-legal-rag-qdrant-1 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
# → 172.22.0.2

# Tunnel to container IP (not localhost:6333)
ssh -f -N -L 6334:172.22.0.2:6333 root@SERVER_IP
```

Use QDRANT_URL=http://localhost:6334 locally. Terminology: "eval local → Qdrant server" not "server eval".

---
*Added via Oracle Learn*
