---
title: ## Source Expansion Floods LLM Context — Removed
tags: [rag, context-flooding, reranker, source-expansion, llm-context]
created: 2026-04-14
source: rrr: gnim-oracle/thai-legal-rag 2026-03-08
project: github.com/gnim-oracle/thai-legal-rag
---

# ## Source Expansion Floods LLM Context — Removed

## Source Expansion Floods LLM Context — Removed

Adding extra chunks from documents already in retrieval top-K ("source expansion") causes catastrophic LLM performance degradation. Mechanism: pulls ALL chunks from a source via metadata lookup, selecting longest/most relevant ones. Combined with MMR (15) + source completion (up to 4/source) + glossary injection (3), total context balloons to 40+ chunks, drowning the signal.

**Evidence**: eval with source_lookup=None → TC-001 PASS. With source_lookup enabled → TC-001 FAIL + 16 other TCs failed. Only variable changed was `source_lookup`.

**Rule**: More context is not better context. Each injection mechanism must be tested in isolation AND in combination. The reranker's job is to select the BEST 15-20 chunks, not stuff every possibly-relevant chunk into prompt. Trust retriever + MMR to pick winners.

**Feature removed from codebase** after this finding.

---
*Added via Oracle Learn*
