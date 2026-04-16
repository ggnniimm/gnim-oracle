---
title: ## Concurrent Index Rebuild Causes Dedup Race Condition
tags: [dedup, faiss, concurrency, race-condition, indexing]
created: 2026-04-14
source: rrr: gnim-oracle/thai-legal-rag 2026-03-09
project: github.com/gnim-oracle/thai-legal-rag
---

# ## Concurrent Index Rebuild Causes Dedup Race Condition

## Concurrent Index Rebuild Causes Dedup Race Condition

Running two index rebuilds concurrently causes dedup.db race condition where one process's entries are seen by the other → 5500+ chunks silently skipped → index has only 966/1230 sources instead of full set.

**Symptoms**: Eval score drops (44→40/48). Total unique sources 966 instead of 1230. Specific files have 0 chunks in FAISS but are marked as indexed in dedup.db. `is_indexed()` returns True for chunks not in FAISS.

**Rule**: NEVER run concurrent index rebuilds. Always wait for one to complete before starting another. Verify by checking that dedup.db and faiss_index/index.faiss have matching timestamps from the same build.

---
*Added via Oracle Learn*
