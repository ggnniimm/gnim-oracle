---
title: ## Thai Legal วรรค Splitting Lessons (2026-02-14 to 2026-02-17)
tags: [thai-legal, varak, paragraph-splitting, gemini, post-processing, caching, regex]
created: 2026-04-14
source: retro: 2026-02-14 to 2026-02-17 วรรค sessions
---

# ## Thai Legal วรรค Splitting Lessons (2026-02-14 to 2026-02-17)

## Thai Legal วรรค Splitting Lessons (2026-02-14 to 2026-02-17)

**Gemini-first is simpler for semantic tasks**: Don't design "heuristic + Gemini fallback" when heuristic can succeed incorrectly. A fallback triggered on failure ≠ fallback triggered on wrong result. Blank-line splitting finding >1 result doesn't mean those splits are correct — they can be semantically wrong.

**Belt-and-suspenders for cache + processing**: When cached data passed through an old processing stage, re-apply processing at read-time. Don't trust cache to be clean.

**Post-processing > prompt engineering for deterministic rules**: List item merging `(๑)(๒)(๓)` is a rule, not a semantic task. 2-pass post-processor is more reliable: Pass 1 merges list markers into parent paragraphs, Pass 2 catches orphan continuation fragments (ตาม, แต่, และ after line break).

**Accept single results from AI**: Discarding valid single-paragraph Gemini output caused unnecessary fallbacks to worse heuristics. `len(result) >= 1` is the right condition.

**Thai legal structure is hierarchical**: ข้อ → วรรค → อนุข้อ → วรรคย่อย. Flat `paragraphs[]` list loses information. Don't conflate วรรค (paragraph) with อนุข้อ (sub-item) — they are different levels.

**Thai law regex is reliable**: Cross-references follow `มาตรา\s+[๐-๙]+` — highly regular, no LLM needed. 30-char lookbehind for keyword classification works consistently.

**Three-tier spot-checking**: Verify many/few/one (5 วรรค, 2 วรรค, 1 วรรค) to cover branching logic without exhaustive testing.

**Communicate encoding tradeoffs before commit**: Thai diacritic filenames (`ข้อ` vs `ขอ`) work on Linux but may cause issues. Explain tradeoff and ask before generating 223 files.

---
*Added via Oracle Learn*
