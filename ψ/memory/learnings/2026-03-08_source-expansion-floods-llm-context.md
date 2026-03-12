# Source Expansion Floods LLM Context

**Date**: 2026-03-08
**Source**: rrr: gnim-oracle/thai-legal-rag
**Confidence**: High (reproduced: 44→31/48, isolated to single variable)

## Pattern

Adding extra chunks from documents already in the retrieval top-K ("source expansion") causes catastrophic LLM performance degradation. The mechanism pulls ALL chunks from a source via metadata lookup, selecting the longest/most relevant ones. Combined with MMR selection (15) + source completion (up to 4/source) + glossary injection (3), the total context balloons to 40+ chunks, drowning the signal.

## Evidence

- Eval with source_lookup=None + query: TC-001 PASS
- Eval with source_lookup enabled: TC-001 FAIL (and 16 other TCs)
- The only variable changed was `source_lookup` parameter

## Rule

**More context is not better context.** Each injection mechanism must be tested in isolation AND in combination. The reranker's job is to select the BEST 15-20 chunks, not to stuff every possibly-relevant chunk into the prompt. Trust the retriever + MMR to pick winners.

## Related

- Dedup pool increase (5x→8x) was helpful — more candidates for MMR to choose from
- Glossary injection (3 chunks) was helpful in isolation — needs re-verification with source expansion removed
- Source completion (4/source) was helpful — injects sibling chunks from docs already selected
