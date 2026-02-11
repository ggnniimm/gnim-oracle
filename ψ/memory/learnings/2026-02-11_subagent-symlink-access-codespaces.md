# Subagent Symlink Access in Codespaces

**Date**: 2026-02-11
**Source**: rrr: gnim-birth-session
**Tags**: subagent, symlink, codespaces, permissions, learn

## Pattern

Haiku subagents spawned via the Task tool cannot follow symlinks that point outside the working directory (e.g., from `ψ/learn/*/origin/` to `~/ghq/github.com/...`).

## Context

During /awaken, the /learn skill cloned repos via ghq and created symlinks in ψ/learn/. Three parallel Haiku agents were launched to explore the code, but all three failed with permission denied errors on Read, Bash, and Grep tools.

## Solution

Read files directly from the main agent using the full ghq path:
```
/home/codespace/ghq/github.com/Owner/Repo/path/to/file.md
```

The main agent (Opus) has access to these paths. Subagents do not.

## Takeaway

For /learn in Codespaces environments: skip the subagent exploration and read key files directly from the main agent. This also produces deeper understanding since you engage with the content firsthand rather than through summaries.
