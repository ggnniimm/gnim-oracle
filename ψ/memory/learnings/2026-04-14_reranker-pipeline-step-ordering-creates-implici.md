---
title: ## Reranker Pipeline Step Ordering Creates Implicit Dependencies
tags: [rag, retrieval, reranker, pipeline, glossary, thai-legal-rag]
created: 2026-04-14
source: Oracle Learn
---

# ## Reranker Pipeline Step Ordering Creates Implicit Dependencies

## Reranker Pipeline Step Ordering Creates Implicit Dependencies

### Context
Thai Legal RAG — TC-042: document 49821 stuck at dedup position 28, never entering MMR's top 15.

### Pattern: Glossary Injection Must Precede Source Expansion
In a multi-step retrieval pipeline, order matters:
1. Glossary injection (rescue low-ranked docs matching 2+ glossary terms)
2. Source expansion (expand chunks from each source, glossary sources first)

Injecting AFTER expansion = newly injected source never gets expanded.
Injecting BEFORE + expanding last = glossary source at position 19 gets skipped when 5-source limit hit.
Fix: priority-sort glossary-injected sources to expand first.

### Pattern: Selection Criteria Should Match Injection Reason
Source expansion by default picks "longest 2 chunks per source." But for glossary-injected sources, pick by "most glossary term matches in chunk" — the specific phrase you need may be in a shorter chunk.

### Pattern: Small Targeted Mechanisms Beat Parameter Tuning
Glossary injection (~30 lines) solves a retrieval problem that would otherwise require:
- Increasing top_k (affects all queries)
- Adjusting reranking weights (unpredictable side effects)
- Index modification

Targeted rescue mechanisms have contained blast radius.

### Pattern: Reranker Diagnostics Are Worth Building
Building a diagnostic that shows full reranker pipeline state (glossary matches, dedup position, source expansion order, final context) for a query saves significant iteration time. Each debugging cycle otherwise requires a new ad-hoc script.

---
*Added via Oracle Learn*
