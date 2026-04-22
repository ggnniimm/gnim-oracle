---
title: Stale worktrees accumulate silently. A worktree created for a branch experiment 
tags: [git, worktree, cleanup, safety, nothing-is-deleted]
created: 2026-04-18
source: rrr: gnim-oracle-qdrant
project: github.com/ggnniimm/gnim-oracle
---

# Stale worktrees accumulate silently. A worktree created for a branch experiment 

Stale worktrees accumulate silently. A worktree created for a branch experiment can survive weeks unnoticed with untracked ψ/ files inside. `git worktree remove` warns "contains modified or untracked files" — treat this as a checkpoint, not an obstacle. Always inspect before --force. Add `git worktree list` to /standup or /recap to surface stale worktrees early.

---
*Added via Oracle Learn*
