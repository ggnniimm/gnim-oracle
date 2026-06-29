---
name: destructive-defaults-are-tech-debt
description: Any sync/cleanup script that defaults to destructive behavior (rsync --delete, force, rm -rf) is tech debt from minute one
metadata:
  type: feedback
---

When writing sync/cleanup scripts, **never default to destructive behavior**. Make destruction opt-in with an explicit flag + warning.

**Examples to avoid as defaults:**
- `rsync --delete` (removes dst files missing on src)
- `git push --force` (overwrites remote history)
- `rm -rf` without confirmation
- `DROP TABLE` without IF EXISTS check

**Why:** 2026-05-28 — sync_md.sh shipped with `rsync --delete` as default. Worked fine while local was a subset of prod. Then prod accumulated 518 orphan files (law section files in subdirs, all with structured metadata). A casual `./sync_md.sh push` would have deleted all 518 in seconds. Caught only because Ming asked for a "complete" diff check, exposing `*deleting` lines I hadn't been filtering for.

**How to apply:** Before adding `--delete`/`--force`/etc. as default in any script:
1. Ask: "If the source is empty by mistake, should the destination become empty too?"
2. If no → make the flag opt-in
3. When the flag IS set, print a warning before action: `⚠️  --delete enabled: N files will be removed from destination`

**Bonus rule:** Before any "prune" operation between two stores (local ↔ prod, repo ↔ remote, etc.), pull the candidate-for-deletion side first. Local becomes a backup snapshot — decisions can be revisited without data loss.

Related: [[check-filter-before-debug-empty]], [[verify-before-fix-known-fail]] — all three are "slow down, verify, confirm" disciplines.
