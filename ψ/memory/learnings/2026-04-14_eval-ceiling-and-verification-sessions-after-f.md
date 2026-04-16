---
title: ## Eval Ceiling and Verification Sessions
tags: [eval, ceiling, verification, llm-variance, branch-discipline]
created: 2026-04-14
source: Thai Legal RAG eval 66/66 2026-03-20
---

# ## Eval Ceiling and Verification Sessions

## Eval Ceiling and Verification Sessions

After fixing all retrieval gaps with cross-ref injection, category boost, rescue phrases, and law-aware chunking, remaining variance is purely generation-level. Same query, same retrieved docs, different LLM output each run.

**Eval ceiling** for Thai Legal RAG with keyword-based must_contain: 64-66/66 = 97-100%. Not fixable with retrieval techniques — chunks are there but model generates differently.

**Verification sessions** (< 2 hours, dedicated to "commit, verify, plan next") are high-value:
- Catch orphaned process issues (e.g., Qdrant lock) before they compound
- Confirm fixes from long creative sessions survive fresh context
- Provide clean decision point: PR, iterate, or pivot

**Branch scope discipline**: Keep branches focused. Multiple unrelated features in one branch makes PR review harder. Merge frequently.

---
*Added via Oracle Learn*
