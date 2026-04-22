---
title: RAG miscitation fix requires TWO parts: (1) state what the document IS about, (2
tags: [rag, hallucination, citation, thai-legal-rag, prompt-engineering]
created: 2026-04-18
source: rrr: gnim-oracle-qdrant
---

# RAG miscitation fix requires TWO parts: (1) state what the document IS about, (2

RAG miscitation fix requires TWO parts: (1) state what the document IS about, (2) explicitly state what it is NOT about. "อย่าอ้างหนังสือฉบับนี้เป็นหลักฐานว่า X" in บทสรุปสำหรับสืบค้น is a valid negative annotation that prevents LLM from using the document for wrong claims. Category confusion needs different fix than direction confusion.

---
*Added via Oracle Learn*
