---
name: Recency boost can override canonical authority in legal RAG
description: Newer secondary sources score higher than older canonical sources due to RECENCY_BOOST
type: project
date: 2026-04-18
---

In Thai legal RAG, old ข้อหารือ documents (e.g. 22315 from 2021) are often THE canonical source for a principle. But secondary sources from 2024-2025 that APPLY or CITE those principles get a higher recency boost, causing them to rank above the canonical source.

**Example**: 22315 (2021) had weighted score 1.0083. 51385 (Dec 2025) had 1.0248 — entirely due to recency (4% boost vs 0.8%). Even after removing 51385's cross-ref injection, 51385 still ranked above 22315.

**Fix applied**: `_CANONICAL_BOOSTS` in reranker.py — when query contains specific keywords, multiply matching source's weighted_score by a factor (1.06) before MMR.

```python
_CANONICAL_BOOSTS = [
    (["ตรวจรับ", "งวดสุดท้าย"], "22315", 1.06),
]
```

**Why:** RECENCY_BOOST was designed as a tiebreaker for equally relevant docs. For Thai legal ข้อหารือ, the original ruling IS the authority regardless of age.

**How to apply:** When a ข้อหารือ document is known to be canonical for a specific principle but keeps getting outranked by newer docs, add a `_CANONICAL_BOOSTS` entry with the query keywords that identify that topic.
