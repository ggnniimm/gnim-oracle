---
name: stale-worktrees-accumulate-silently
description: Git worktrees left uncleaned for weeks can hold untracked ψ/ files that risk being lost on force-remove
type: project
---

# Stale worktrees accumulate silently

Worktrees don't show up in git status, /recap, or /standup by default. A worktree created on 2026-03-13 (`gnim-oracle-embedding-v2`) survived 35 days unnoticed with 2 untracked ψ/ files inside — they would have been permanently lost without the `git worktree remove` safety warning.

**Why:** No routine checks for stale worktrees. Once a branch experiment ends, the worktree is often forgotten.

**How to apply:** Add `git worktree list` to /standup or /recap to surface stale worktrees early. Always inspect untracked files before `--force` removing a worktree. The warning "contains modified or untracked files" is a checkpoint — stop and check, don't bypass.
