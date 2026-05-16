---
name: prod-local-src-drift
description: How prod source code drifted 5 weeks from local without anyone noticing — detection pattern and prevention
metadata:
  type: project
---

# Prod-Local Source Code Drift Detection Pattern

**Date discovered**: 2026-05-15 (during prod-cleanup arc)
**Context**: thai-legal-rag on `root@31.97.188.155`. 101 inactive MDs were contributing ~4,707 chunks to prod RAG retrieval despite being flagged `status: inactive` in their frontmatter.

## How It Was Discovered

Not by a process — by accident. We noticed prod had 34,703 chunks where we expected ~30K after corpus cleanup. Running a spot-check on an inactive MD (`ว139`) via `docker exec` showed it still returning chunks. That led to grepping `md_loader.py` inside the container and finding the `status == inactive → return []` guard was **missing from prod** despite being present locally.

The file was dated `2026-04-02` on the host (a 5-week-old snapshot). Local was at commit `6c1377f` (2026-05-10). The deploy workflow used `scp` of **specific files only** — the inactive filter was added later and never made it to prod.

## Root Cause

Six source files diverged between local and prod. Only one (`md_loader.py`) was a correctness bug. The others were dead code on prod (removed locally, still on prod but inert).

The deploy workflow's `scp`-specific-files approach means any code added *after* the last targeted deploy is invisible to prod. There is no diff step before deploying.

## Detection Pattern

Before every reindex or eval run, extract prod source files and diff against local:

```bash
# Pull the files that matter
docker cp thai-legal-rag-app-1:/app/src/ingestion/md_loader.py /tmp/prod_md_loader.py
diff /tmp/prod_md_loader.py ψ/lab/thai-legal-rag/src/ingestion/md_loader.py

# Or for the whole src/ tree
docker exec thai-legal-rag-app-1 find /app/src -name '*.py' -exec md5sum {} \; > /tmp/prod_checksums.txt
find ψ/lab/thai-legal-rag/src -name '*.py' -exec md5sum {} \; | sed 's|ψ/lab/thai-legal-rag/app/||' > /tmp/local_checksums.txt
diff /tmp/prod_checksums.txt /tmp/local_checksums.txt
```

Fast version (just the ingestion layer — highest risk):
```bash
for f in md_loader.py ocr.py index_md_folder.py; do
  docker cp thai-legal-rag-app-1:/app/src/ingestion/$f /tmp/prod_$f 2>/dev/null || \
  docker cp thai-legal-rag-app-1:/app/pipeline/$f /tmp/prod_$f 2>/dev/null
  echo "=== $f ===" && diff /tmp/prod_$f ψ/lab/thai-legal-rag/src/ingestion/$f 2>/dev/null || \
  diff /tmp/prod_$f ψ/lab/thai-legal-rag/pipeline/$f 2>/dev/null
done
```

## Prevention

Add a **deploy-verify step** to the handoff template whenever a reindex, eval gate, or prod-touching operation is planned:

> **Pre-deploy check**: `docker cp` key source files from prod container → diff against local. Any diff = decide: surgical patch or full redeploy. Document the outcome.

The surgical patch workflow (when diff is small + isolated) is in [[surgical-patch-prod-local]].

## Why It Went Undetected for 5 Weeks

- Eval scores were still acceptable (77-84/84) — the inactive-chunk pollution diluted retrieval but didn't cause catastrophic failure
- No automated drift detection in the deploy workflow
- Memory said "prod is up to date" — but memory reflects intent at deploy time, not current state

**Why:** [[verify-production-before-deploy]] — prod host has no git; always grep production code before deciding what to deploy. This incident proved the same rule applies to *source files inside containers*, not just configs.

**How to apply:** Before any prod reindex or eval, run the 3-file spot check above. If diff is non-empty, decide before indexing — stale code producing bad chunks wastes the entire reindex cost.

Cross-links: [[verify-production-before-deploy]] [[memory-vs-filesystem]] [[surgical-patch-prod-local]]

## Numbers

- Files diffed: 6
- Files with correctness impact: 1 (`md_loader.py`, 3 lines at line ~153)
- Chunks removed once fixed: 3,686 (inactive → 0)
- Prod chunks before: 34,703 → after: 31,017 (post-delete) → 31,368 (post-reindex)
- Eval after fix: 82/84 (baseline holds)
- Days of drift: ~44 days (2026-04-02 → 2026-05-15)
