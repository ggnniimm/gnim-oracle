---
title: ## Always Confirm Environment Before Debugging
tags: [debugging, workflow, environment, production, docker, streamlit]
created: 2026-04-14
source: 2026-04-11 learning
---

# ## Always Confirm Environment Before Debugging

## Always Confirm Environment Before Debugging

When a user reports a bug in UI/app, the first question must be **"ทดสอบที่ไหน?"** (which environment?) before starting to fix anything.

**What Happened**: Spent 4 hours fixing bugs on localhost even though the user was using mwaprocure.gnim.cloud the whole time. All work (patch Qdrant local, patch BM25 local, restart local Streamlit) had zero effect on the real problem.

**Root Cause of Actual Bug**: Key mismatch in `streamlit_app.py`:
- `_build_source_map` stored URL under key `"url"`
- New answer rendering fetched with `s.get("drive_id", "")` ← key didn't exist
- Result: links always empty even though data was correct

**Rules**:
1. Ask environment first: localhost? mwaprocure? which server?
2. Read code before assuming: grep for the key being used before assuming it's a data problem
3. Verify yourself before telling user: run pipeline, see actual result, before reporting
4. Fix only what was asked: don't add features during a bug fix session

**Docker Deploy Rules**:
- `docker compose restart` = uses old image, doesn't pick up code changes
- `docker compose build app && docker compose up -d app` = picks up new code
- Volume mount is only `./data`, not `./app` or `./src`

---
*Added via Oracle Learn*
