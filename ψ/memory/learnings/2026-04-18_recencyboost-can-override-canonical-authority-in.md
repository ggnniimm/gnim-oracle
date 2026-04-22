---
title: RECENCY_BOOST can override canonical authority in legal RAG. Old ข้อหารือ docume
tags: [rag, reranker, recency-boost, canonical, thai-legal]
created: 2026-04-18
source: rrr: thai-legal-rag
---

# RECENCY_BOOST can override canonical authority in legal RAG. Old ข้อหารือ docume

RECENCY_BOOST can override canonical authority in legal RAG. Old ข้อหารือ documents (2021) are outranked by newer secondary sources (2025) that cite them, purely due to recency boost (+4% vs +0.8%). Fix: _CANONICAL_BOOSTS in reranker — when query contains specific keywords, multiply canonical source weighted_score by 1.06 before MMR. Pattern: (query_keywords_all_must_match, source_name_substring, boost_factor).

---
*Added via Oracle Learn*
