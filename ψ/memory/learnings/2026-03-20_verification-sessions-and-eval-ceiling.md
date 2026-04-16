# Verification Sessions & the 66/66 Eval Ceiling

**Date**: 2026-03-20
**Context**: thai-legal-rag eval hit 66/66 clean sweep after committing yesterday's fixes

## Verification Sessions

Short sessions (< 2 hours) dedicated to "commit, verify, plan next" are high-value:
- Catch orphaned process issues (Qdrant lock) before they compound
- Confirm that fixes from long creative sessions survive a fresh context
- Provide a clean decision point: PR, iterate, or pivot

## Eval Ceiling: 64-66/66

With all retrieval techniques in place (cross-ref injection, category boost, rescue phrases, law-aware chunking), the remaining variance is purely generation-level:
- Same query, same retrieved docs, different LLM output each run
- TC-029 (ร้อยละ 0) is the most visible example
- No retrieval fix exists for this — the chunks are there, the model just generates differently

Next lever: either accept the variance band (64-66) or explore more deterministic generation (structured output, constrained decoding, post-processing).

## Branch Scope Discipline

feat/admin-court-judgments grew from 1 feature to 11 commits spanning infra, retrieval, generation, and eval. Worked fine for solo rapid iteration but makes PR review harder. For future: consider merging more frequently to keep branches focused.
