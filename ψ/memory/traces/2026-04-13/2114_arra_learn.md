---
query: "arra_learn"
target: "gnim-oracle-qdrant"
mode: smart→deep
timestamp: 2026-04-13 21:14
friction_score: 0.7
coverage: [oracle, files, cross-repo]
confidence: high
---

# Trace: arra_learn

**Target**: gnim-oracle-qdrant
**Mode**: smart→deep (Oracle miss → Wave 1) | **Friction**: 0.7 | **Confidence**: high
**Time**: 2026-04-13 21:14

## Oracle Results
None — Oracle DB empty (just set up today)

## Files Found

**Implementation** (Soul-Brews-Studio/arra-oracle-v3):
- `src/tools/learn.ts` lines 22–48 — MCP tool definition (`learnToolDef`, `handleLearn`)
- `src/cli/commands/learn.ts` lines 5–31 — CLI: `arra learn --pattern "<text>" [--source] [--concepts] [--project]`

**Skill references** (.claude/skills/):
- `learn/SKILL.md` — calls `arra_learn({ pattern, concepts, source })` after writing docs
- `rrr/SKILL.md` — calls `arra_learn({ pattern, concepts, source: "rrr: REPO" })` after retrospective
- `awaken/SKILL.md` — calls `arra_learn(...)` after re-awakening
- `oracle-family-scan/SKILL.md` — calls `arra_learn(...)` after family scan

## Git History
Not searched (Wave 1 sufficient)

## GitHub Issues/PRs
Not searched (Wave 1 sufficient)

## Cross-Repo Matches
- `Soul-Brews-Studio/arra-oracle-v3` — source of truth for implementation

## Oracle Memory
None (DB empty)

## What arra_learn Does

**MCP Tool**: `mcp__arra-oracle-v2__arra_learn`

Adds new patterns/learnings to the Oracle knowledge base.

**Parameters**:
- `pattern` (required, string): The learning content (multi-line OK)
- `source` (optional, string): Attribution (defaults to "Oracle Learn")
- `concepts` (optional, array): Tags e.g. `["git", "safety", "mcp"]`
- `project` (optional, string): Repo attribution — accepts `github.com/owner/repo`, `owner/repo`, local path, or GitHub URL

**Behavior**:
1. Slugifies first 50 chars of pattern → `YYYY-MM-DD_slug.md`
2. Writes frontmatter (title, tags, created, source, project) to `ψ/memory/learnings/`
3. Inserts into `oracleDocuments` SQLite table (type: `learning`)
4. Indexes in FTS5 for future `arra_search` queries

## Friction Analysis
**Score**: 0.7 — Visible (Files + high confidence)
**Coverage**: oracle ✓, files ✓, cross-repo ✓ | git ✗, github ✗
**Goal check**: Yes — found exact implementation, parameters, and integration points.

## Summary
`arra_learn` is an MCP tool provided by `arra-oracle-v3` (local: `~/.ghq/github.com/Soul-Brews-Studio/arra-oracle-v3`). Now connected as `mcp__arra-oracle-v2__arra_learn`. Skills call it after `/learn`, `/rrr`, `/awaken` to index knowledge for future `arra_search`. Oracle DB was empty until today (first setup 2026-04-13).
