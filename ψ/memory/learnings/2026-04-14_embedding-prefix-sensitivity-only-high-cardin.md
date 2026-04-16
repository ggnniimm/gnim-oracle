---
title: ## Embedding Prefix Sensitivity — Only High-Cardinality Metadata
tags: [embedding, metadata, prefix, retrieval, rag]
created: 2026-04-14
source: Thai Legal RAG metadata prefix experiment 2026-03-03
---

# ## Embedding Prefix Sensitivity — Only High-Cardinality Metadata

## Embedding Prefix Sensitivity — Only High-Cardinality Metadata

Adding metadata to chunk text before embedding can HURT retrieval if the metadata has low cardinality.

**Evidence**: Original prefix `[ref_number | date | category]` → 44/44 eval. Adding topic+subtopic+laws_referenced → 36/44 (-8 TCs). Reverted → 44/44.

**Why**: 100-char prefix on 400-char chunk = 25% of semantic signal is metadata. Low-cardinality fields like `topic` = "การจัดซื้อจัดจ้าง" for 95% of docs — adds no discriminative power, just dilutes content signal.

**Only prepend metadata with high cardinality and genuine discriminative power**:
- `ref_number` — unique per document
- `date` — varies across docs  
- `category` — 3-5 distinct values

**Do NOT prepend**: `topic` (same for 95%), `laws_referenced` (too long), `subtopic` (marginal value)

**must_contain corollary**: Use shortest natural form LLM consistently generates. "ขยายเวลา" > "ขยายระยะเวลา". Avoid synonyms LLM freely substitutes: "ไม่อาจ" ↔ "ไม่สามารถ".

---
*Added via Oracle Learn*
