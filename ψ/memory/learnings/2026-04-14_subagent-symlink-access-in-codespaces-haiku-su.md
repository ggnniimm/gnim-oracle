---
title: ## Subagent Symlink Access in Codespaces
tags: [subagent, symlink, codespaces, permissions]
created: 2026-04-14
source: rrr: gnim-birth-session 2026-02-11
---

# ## Subagent Symlink Access in Codespaces

## Subagent Symlink Access in Codespaces

Haiku subagents spawned via the Task tool cannot follow symlinks that point outside the working directory (e.g., from `ψ/learn/*/origin/` to `~/ghq/github.com/...`). All three fail with permission denied errors on Read, Bash, and Grep tools.

**Solution**: Read files directly from the main agent using the full ghq path. The main agent (Opus) has access to these paths. Subagents do not.

**Takeaway**: For /learn in Codespaces environments: skip the subagent exploration and read key files directly from the main agent. This also produces deeper understanding since you engage with the content firsthand rather than through summaries.

---
*Added via Oracle Learn*
