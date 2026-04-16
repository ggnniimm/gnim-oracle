---
title: ## Qdrant Local Mode = Single-Process Lock, Use Docker for Concurrent Access
tags: [qdrant, docker, concurrent-access, local-mode, server-mode]
created: 2026-04-14
source: Thai Legal RAG Qdrant migration 2026-03-17
---

# ## Qdrant Local Mode = Single-Process Lock, Use Docker for Concurrent Access

## Qdrant Local Mode = Single-Process Lock, Use Docker for Concurrent Access

Qdrant `QdrantClient(path=...)` holds an exclusive file lock — only one process can access at a time. Running Streamlit + export job simultaneously causes "Storage folder already accessed by another instance" error. Also not recommended for >20,000 points.

**How to apply**: Use `QDRANT_URL=http://localhost:6333` (Docker server mode) for any setup where more than one process needs concurrent Qdrant access. `qdrant_store.py` supports both modes via env var — `QDRANT_URL` takes priority over path mode.

In Docker: Streamlit app uses `QDRANT_URL=http://qdrant:6333` (internal network). On Mac: `QDRANT_URL=http://localhost:6333`.

---
*Added via Oracle Learn*
