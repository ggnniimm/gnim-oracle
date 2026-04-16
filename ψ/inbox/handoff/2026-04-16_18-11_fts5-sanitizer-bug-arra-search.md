# FTS5 Sanitizer Bug in arra_search (MCP Tool)

**Status**: Reported (GitHub issues disabled on upstream repo — documented internally)
**Discovered**: 2026-04-16 during /rrr session in gnim-oracle-qdrant
**Severity**: Medium — user-facing queries with `[]`, `{}`, `<>`, `;`, `\` throw errors
**Upstream**: https://github.com/Soul-Brews-Studio/arra-oracle-v2 (issues disabled)

## Problem

`arra_search({ query: "test [bracket] syntax" })` → `Error: fts5: syntax error near "["`

Common real-world queries break:
- `citation numbering [2][2][3] per document RAG`
- Code snippets with `<tag>` or `{placeholder}`
- Semicolon-separated clauses

## Root Cause

Two divergent sanitizers in the codebase:

**Incomplete** (used by MCP `arra_search`):
```
src/tools/search.ts:72-84 sanitizeFtsQuery()
  .replace(/[?*+\-()^~"':.\/]/g, ' ')   ← missing [] {} <> ; \
```

**Complete** (used by another search path):
```
src/server/handlers.ts:43-45
  .replace(/[?*+\-()^~"':;<>{}[\]\\\/]/g, ' ')
```

## Fix

Either:
1. Update `search.ts:74` regex to match `handlers.ts:45`
2. Extract shared helper in `src/utils/fts.ts` and import from both sites (recommended — prevents future drift)

## Next Actions (for maintainer or next session)

- Since upstream issues disabled: submit PR directly to Soul-Brews-Studio/arra-oracle-v2
- Or: patch locally at `~/.arra-oracle/node_modules/arra-oracle-v2/src/tools/search.ts:74`
  (but will be overwritten on next package update)
- Workaround in the meantime: strip brackets from queries before calling arra_search

## Reproduction

```javascript
// Fails:
arra_search({ query: "test [x]" })  // fts5 syntax error

// Works (same content, brackets removed):
arra_search({ query: "test x" })    // returns results
```

## Related

- Session retro: `ψ/memory/retrospectives/2026-04/16/16.29_chat-history-export-all-users.md`
- Discovered while testing: `ψ/memory/learnings/2026-04-16_verify-user-state-before-debugging.md`
