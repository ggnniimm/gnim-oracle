---
title: ## Long Session + Project Early Growth Patterns (2026-02-13)
tags: [session-management, architecture, planning, git, secrets, workflow, patterns]
created: 2026-04-14
source: retro: 2026-02-13 all-sessions-dig
---

# ## Long Session + Project Early Growth Patterns (2026-02-13)

## Long Session + Project Early Growth Patterns (2026-02-13)

**Long sessions (400+ min) produce architecture debt**: Session 4 (438 min) built a pipeline, Session 7 (791 min) rebuilt it from scratch. The redesign was necessary but costly. Better upfront architecture sketch prevents rebuilds.

**Start new project modules with a plan file, not code**: Writing a plan first (even 1 page) prevents the "code first, regret later" cycle. In 3 days: 30+ commits, full production-grade RAG pipeline — but with one costly rebuild.

**Plan paths drift from actual filesystem**: If a plan references `pipeline/streamlit_app.py` but code lives at `app/streamlit_app.py`, every handoff creates confusion. Keep plan paths in sync with actual filesystem.

**Always scan git status before staging in lab directories**: `credentials.json` and `token.json` sat untracked for multiple sessions near a `git add .` away from being committed. Lab directories accumulate secrets silently.

**Ming's working pattern**: Long sessions → short fix sessions. Plans arrive at session start. LightRAG is always the complexity spike.

---
*Added via Oracle Learn*
