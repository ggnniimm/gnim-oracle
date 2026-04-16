---
name: Qdrant local mode = single-process lock, use Docker for concurrent access
description: Qdrant path mode blocks concurrent processes; QDRANT_URL server mode (Docker) allows simultaneous access from Streamlit, eval, and export jobs
type: project
---

Qdrant `QdrantClient(path=...)` holds an exclusive file lock — only one process can access at a time. Running Streamlit + export job simultaneously causes "Storage folder already accessed by another instance" error.

**Why:** Discovered when Streamlit failed to load because the HTML export job held the Qdrant lock. Local mode is also not recommended for >20,000 points (warning visible in logs — collection has 29,501 points).

**How to apply:** Use `QDRANT_URL=http://localhost:6333` (Docker server mode) for any setup where more than one process needs concurrent Qdrant access. `qdrant_store.py` now supports both modes via env var — QDRANT_URL takes priority over path mode.
