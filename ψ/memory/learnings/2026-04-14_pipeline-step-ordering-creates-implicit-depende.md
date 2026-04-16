---
title: ## Pipeline Step Ordering Creates Implicit Dependencies
tags: [pipeline, architecture, rag, reranker, ordering]
created: 2026-04-14
source: Thai Legal RAG reranker pipeline 2026-03-07
---

# ## Pipeline Step Ordering Creates Implicit Dependencies

## Pipeline Step Ordering Creates Implicit Dependencies

When adding a new step to a multi-stage pipeline, placement relative to other steps creates implicit dependencies. A step that injects new items must come BEFORE any step that expands or enriches those items.

**Example**: Reranker pipeline: MMR selection → source completion → source expansion → glossary injection
Problem: Glossary injection added doc 49821, but source expansion had already run — 49821 only had anchor chunk, not content chunks.
Fix: Reorder to MMR → source completion → glossary injection → source expansion. Now glossary-injected sources get expanded too.

**Additional insight**: When a step has a processing limit ("expand top 5 sources"), items added by earlier steps compete for those slots. Injected items may need priority. Enrich criteria should be context-aware (why was this item injected?).

**Rule for inject → enrich stages**:
1. Inject step must precede enrich step
2. Injected items may need priority in enrich step
3. Enrich criteria should match injection reason

---
*Added via Oracle Learn*
