# `docker compose restart` does NOT reload `.env`

**Date**: 2026-05-08
**Context**: thai-legal-rag prod deploy of GA migration

## The trap

Edited prod `/app/thai-legal-rag/.env` (added `EMBEDDING_MODEL=gemini-embedding-2`, changed location to `global`), then ran:

```bash
docker compose restart app
```

Container came back up, but `docker exec ... env` showed the **OLD** env vars. Service was still pointing at us-central1 + preview model. Confirmed by: `docker exec ... python3 -c 'import os; print(os.environ["GOOGLE_CLOUD_LOCATION"])'` → `us-central1`.

## The cause

`docker compose restart` only restarts the existing container — it does not re-read `.env` or `env_file:` from `docker-compose.yml`. Env vars are baked in at **container creation time**, not at start time.

## The fix

Use `up -d` to recreate the container with new env values:

```bash
docker compose up -d app
```

This stops, removes, and creates a fresh container — picking up the current `.env`. Verify after with:

```bash
docker exec <container> sh -c 'env | grep <YOUR_VAR>'
```

## Bonus gotcha

Even after `up -d`, the embedding model was still wrong. Reason: `src/config.py` had the model **hardcoded** (older version from before yesterday's env-readable change). Env var was correct in the container but config.py overrode it. Fixed with `sed` + `docker compose build app` + `up -d`.

**Two-layer rule**: when behavior doesn't match env, also grep the source for hardcoded values that might shadow it. `os.getenv("X", default)` is env-readable; `X = "literal"` is not.

## Apply when

- Editing prod `.env` and need it to take effect → `up -d`, never `restart`
- Verify with `docker exec ... env` before assuming the change landed
- If env is right but behavior is wrong → grep source for hardcoded shadows
