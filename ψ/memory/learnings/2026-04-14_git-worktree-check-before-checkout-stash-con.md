---
title: ## Git Worktree: Check Before Checkout + Stash Conflict Resolution
tags: [git, worktree, workflow, merge, stash, conflict-resolution]
created: 2026-04-14
source: 2026-04-11 learning
---

# ## Git Worktree: Check Before Checkout + Stash Conflict Resolution

## Git Worktree: Check Before Checkout + Stash Conflict Resolution

In repos with multiple worktrees (e.g., `gnim-oracle` + `gnim-oracle-qdrant` sharing the same git repo), always run `git worktree list` before checking out any branch.

**What Happened**: Tried `git checkout main` in `gnim-oracle-qdrant` to merge, got error: `fatal: 'main' is already used by worktree at '/Users/mingsaksaengwilaipon/gnim-oracle'`. Fix: `cd` to that worktree instead.

**Stash Conflict Resolution Rule**: When `stash pop` has a conflict in append-only data (e.g., JSON array of test cases, JSON array of allowedTools):
- **Keep both sides** — upstream (merged) + stash always
- Never discard stash side without reviewing
- If IDs collide → rename stash entry to new ID (TC-079, TC-080...)

**Rules**:
1. `git worktree list` before checkout every time in a multi-worktree repo
2. Stash = uncommitted work → never drop without checking
3. Merge conflict in JSON array = take both, not either

---
*Added via Oracle Learn*
