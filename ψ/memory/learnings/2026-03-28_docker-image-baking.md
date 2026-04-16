---
name: Docker image baking — restart vs rebuild
description: docker compose restart reuses cached image; source code changes require docker compose build
type: feedback
---

Source code is baked into the Docker image at build time. `docker compose restart` only restarts the container using the existing image — it does NOT pick up code changes.

**Why:** Learned the hard way when a new UI feature (New Chat button) was invisible after restart. Had to rebuild to see it.

**How to apply:** After any code change to `app/` or `src/`, always run:
```bash
docker compose build app && docker compose up -d app
```
Never just `restart` when you've changed source files.
