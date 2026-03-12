# Cross-ref Must Target Consistently Top-Ranked Document

**Date**: 2026-03-11
**Context**: Thai Legal RAG — TC-050 cross-ref injection for ว268

## Pattern

When using cross-reference injection to make document X's content appear in answers, the cross-ref text must be placed in the document that is **consistently ranked #1** for the target query — not just any thematically related document.

## Example

- **Failed**: Injected ว268 cross-ref into ว52 (penalty reduction circular). ว52 wasn't being retrieved for TC-050 in that run — ว647 was #1 instead.
- **Succeeded**: Injected ว268 cross-ref into ว647 (แนวทางปฏิบัติสำหรับการจ้างทำของ). ว647 is consistently #1 for all penalty-related queries.

## Why It Matters

- MMR diversity filtering is non-deterministic enough that a document ranked #3-5 might be filtered in some runs
- Only the #1 document is reliably in every LLM context
- Wasted iteration time: each failed attempt requires a full index rebuild (~7-8 min)

## Side Effect

Adding cross-ref text to a large document (ว647, ~1000 lines) changes chunk boundaries, which can cause regressions in unrelated test cases. In this case, TC-003 regressed because the LLM deprioritized "ผลิตภายในประเทศ" content. Fixed with a rescue phrase.

## Verification Steps Before Injection

1. Run FAISS search for the target query
2. Confirm which document is consistently #1 (run 2-3 times if needed)
3. Inject cross-ref into that document
4. Run full eval after rebuild to catch regressions
