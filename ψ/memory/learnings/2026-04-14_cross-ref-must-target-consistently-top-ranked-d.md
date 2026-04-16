---
title: ## Cross-Ref Must Target Consistently Top-Ranked Document
tags: [cross-reference, retrieval, rag, injection, thai-legal]
created: 2026-04-14
source: Thai Legal RAG TC-050 cross-ref injection 2026-03-11
---

# ## Cross-Ref Must Target Consistently Top-Ranked Document

## Cross-Ref Must Target Consistently Top-Ranked Document

When using cross-reference injection, the cross-ref text must be placed in the document consistently ranked #1 for the target query — not just any thematically related document.

**Failed**: Injected ว268 cross-ref into ว52 (wasn't being retrieved in that run — ว647 was #1 instead).
**Succeeded**: Injected into ว647 (consistently #1 for all penalty-related queries).

**Why**: MMR diversity filtering is non-deterministic — document ranked #3-5 might be filtered in some runs. Only #1 document is reliably in every LLM context.

**Verification steps before injection**:
1. Run FAISS search for target query
2. Confirm which document is consistently #1 (run 2-3 times)
3. Inject cross-ref into that document
4. Run full eval after rebuild to catch regressions

**Side effect**: Adding cross-ref text to a large document changes chunk boundaries, which can cause regressions in unrelated test cases.

---
*Added via Oracle Learn*
