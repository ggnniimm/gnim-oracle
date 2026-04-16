---
title: ## Legal RAG — doc_type Priority in Reranker
tags: [legal-rag, reranker, doc-type, authority, thai-legal]
created: 2026-04-14
source: Thai Legal RAG session 2026-03-15
---

# ## Legal RAG — doc_type Priority in Reranker

## Legal RAG — doc_type Priority in Reranker

In legal RAG, authority order of sources must be reflected in reranker score — not just semantic similarity. Correct legal authority hierarchy:
1. คำพิพากษา (ศาลปกครอง) — binding legal principles
2. คำวินิจฉัยอัยการสูงสุด — legal interpretation
3. กวจ./กรมบัญชีกลาง — operational guidelines

**Rule**: Add `_CATEGORY_BOOST` in reranker so category "ศาลปกครอง" gets boost >1.0 above กวจ./กรมบัญชีกลาง. Current: `_CATEGORY_BOOST = {"ศาลปกครอง": 1.30, "สำนักงานอัยการสูงสุด": 1.05}` — applied after normalize score, before recency boost.

**Why**: Ming asked "ควรหาแนวทางปฏิบัติที่ดีจากคำพิพากษาก่อน ค่อยไปดู กวจ. ไม่ใช่หรอ?" — old system always surfaced กวจ. first because procedural queries match กวจ. better → answers emphasized procedure over legal principle.

---
*Added via Oracle Learn*
