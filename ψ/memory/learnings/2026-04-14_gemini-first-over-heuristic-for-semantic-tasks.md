---
title: ## Gemini-First Over Heuristic for Semantic Tasks
tags: [gemini, heuristic, semantic, thai-legal, two-phase-trap]
created: 2026-04-14
source: Session — Gemini-first วรรค splitting 2026-02-14
---

# ## Gemini-First Over Heuristic for Semantic Tasks

## Gemini-First Over Heuristic for Semantic Tasks

**Core insight**: "Fallback triggered on failure" ≠ "fallback triggered on wrong result"

Heuristic phase 1 can "succeed wrongly" — produce >1 result but semantically wrong. This means the Gemini fallback never gets called even when the result is incorrect.

**Two-Phase Trap**:
```
phase 1 (heuristic) → if failure → phase 2 (AI)
```
Must ask: "Can phase 1 succeed wrongly?" If yes → phase 2 won't be called when needed → use AI from the start.

**When heuristic is OK**: Task where failure is clear (parse error, empty result), heuristic has high precision, or AI cost is very high.

**When to use AI first**: Semantic boundary detection, Thai text without clear lexical markers, low-cost AI calls (Gemini Flash).

---
*Added via Oracle Learn*
