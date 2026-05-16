# Surgical Patch Pattern for Prod-Local Code Drift

**Date**: 2026-05-16
**Context**: Discovered prod `md_loader.py` was 5 weeks stale (dated 2026-04-02) vs local commit `6c1377f` (2026-05-10). 3-line diff caused 101 inactive files / 3,686 chunks to pollute prod RAG. Needed to deploy the fix without doing a full Docker image rebuild + re-index (which last time took 14h 53m of Vertex AI 429-throttled re-indexing).

## The Pattern

For a small, isolated code fix that needs to land on prod NOW:

```bash
# 1. Backup pre-patch file (for rollback)
docker cp <container>:<path> /tmp/<file>.bak.YYYY-MM-DD

# 2. Confirm clean diff (no surprise prod-local divergence)
docker cp <container>:<path> /tmp/prod.py
diff -u /tmp/prod.py /path/to/local.py
# Verify diff is ONLY the change you intend to deploy

# 3. Copy local file into running container
docker cp /path/to/local.py <container>:<path>

# 4. Verify inside container
docker exec <container> grep -n "<expected change>" <path>

# 5. Bake into a tagged image (survives container recreate)
docker commit <container> <repo>:patched-YYYY-MM-DD-<slug>

# 6. Restart the service so the patched code is loaded
cd /app/<project> && docker compose restart <service>

# 7. Functional verification post-restart
docker exec <container> python3 -c "..."
```

Total time: ~1 minute. Downtime: ~30s (just the restart).

## When to use it

- **Small, isolated diff**: 3 lines, single file, no schema/migration impact
- **Time-critical**: production correctness bug, ongoing data pollution, etc.
- **Full deploy is expensive**: avoiding a multi-hour rebuild/re-index
- **Clean diff verified**: no other prod-local drift in the same file that you'd accidentally clobber

## When NOT to use it

- Multiple files diverged → do a proper deploy
- Schema/data migrations → need orchestration
- Any change requiring image-layer dependencies (new pip packages, etc.)
- Long-term solution: image-tag-drift accumulates if you keep patching

## The image-tag trick (step 5)

`docker commit` creates a new image layer on top of the running container's current state. Tag it with a descriptive name (`patched-2026-05-16-inactive-filter`). This means:
- If the compose file pins `image:` to the original tag, you'd need to update it OR the next `docker compose up` will recreate the container from the OLD image (re-introducing the bug)
- For ad-hoc patching, the named tag is mostly a record-keeping device + safety net
- Plan to bake the change into the canonical Dockerfile + redeploy at the next scheduled deploy

## Anti-pattern to avoid

Just `docker cp` without `docker commit`. The patch lives in the container's writable layer and disappears the moment the container is recreated (`docker compose up -d`, `docker compose down/up`, host reboot). `docker compose restart` preserves it; everything else loses it.

## Detection (the harder part)

The fix is easy once you know prod is stale. The hard part is **detecting** the drift before it causes correctness bugs. See [pending STEP E memo on prod-local drift detection pattern].

## Real session reference

`ψ/memory/retrospectives/2026-05/16/08.36_prod-cleanup-A-B-D-C-82-84.md`

Numbers:
- File: `src/ingestion/md_loader.py`, 3-line diff at line 153
- Backup: `root@31.97.188.155:/tmp/md_loader_prod.bak.2026-05-16`
- Image tag: `thai-legal-rag-app:patched-2026-05-16-inactive-filter`
- Downtime: ~30s (docker compose restart app)
- Verification: inactive MD → 0 chunks, active MD → 12 chunks ✓
- Eval gate: 82/84 baseline holds post-patch
