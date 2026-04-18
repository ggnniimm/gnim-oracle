---
title: Cross-ref in top-ranked doc beats sub-doc when RAG corpus is large (28K+ chunks)
tags: [rag, mmr, cross-ref, retrieval, chunk-size, thai-legal-rag]
created: 2026-04-18
source: rrr: gnim-oracle-qdrant
---

# Cross-ref in top-ranked doc beats sub-doc when RAG corpus is large (28K+ chunks)

Cross-ref in top-ranked doc beats sub-doc when RAG corpus is large (28K+ chunks). MMR diversity penalty blocks sub-docs even with good vector scores (local rank [5] → server rank [24]). Pattern: find the doc that consistently ranks [1] for the target query → add cross-ref bullet summarizing missing doc's key content into its สรุปข้อวินิจฉัย. LLM cites the content even though source shown is the carrier doc. Also: insert cross-ref at BOTTOM of section, not top — inserting at top shifts chunk boundaries (CHUNK_SIZE=400) and can cause regressions in other content.

---
*Added via Oracle Learn*
