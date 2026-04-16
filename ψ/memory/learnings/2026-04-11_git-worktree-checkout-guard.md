---
date: 2026-04-11
tags: [git, worktree, workflow, merge]
---

# Git Worktree: Check Before Checkout

## Pattern

ใน repo ที่มี multiple worktrees (เช่น `gnim-oracle` + `gnim-oracle-qdrant` ใช้ repo เดียวกัน) ต้อง run `git worktree list` ก่อน checkout branch ใดก็ตาม

## What Happened

พยายาม `git checkout main` ใน `gnim-oracle-qdrant` เพื่อ merge แต่ได้ error:
```
fatal: 'main' is already used by worktree at '/Users/mingsaksaengwilaipon/gnim-oracle'
```

เพราะ `main` ถูก checkout ใน `/gnim-oracle` worktree อยู่แล้ว ต้อง cd ไปที่นั่นแทน

## Stash Conflict Resolution Rule

เมื่อ stash pop มี conflict ใน append-only data (เช่น JSON array ของ test cases, JSON array ของ allowedTools):
- **เก็บทั้งสองฝั่ง** — upstream (merged) + stash เสมอ
- ห้าม discard stash side โดยไม่ดูก่อน
- ถ้า ID ซ้ำ → rename stash entry ให้ ID ใหม่ (TC-079, TC-080...)

## Rules

1. `git worktree list` ก่อน checkout ทุกครั้งใน repo ที่มี worktrees
2. Stash = งานที่ยังไม่ commit → อย่า drop โดยไม่ตรวจก่อน
3. Merge conflict ใน JSON array = take both, not either
