---
title: RAG negative annotation — two-part fix for document miscitation: (1) state what 
tags: [rag, hallucination, miscitation, negative-annotation, thai-legal-rag, prompt-engineering]
created: 2026-04-19
source: rrr: gnim-oracle-qdrant
---

# RAG negative annotation — two-part fix for document miscitation: (1) state what 

RAG negative annotation — two-part fix for document miscitation: (1) state what the document IS: "กรณีนี้เกี่ยวกับ X ซึ่งยังมิได้ตรวจรับงานงวดสุดท้าย"; (2) state what it is NOT with explicit "อย่าอ้างหนังสือฉบับนี้เป็นหลักฐานว่า Y". The retrieved chunk is read directly by the LLM — negative instructions embedded in context work as constraints. Category confusion (wrong bucket) ≠ direction confusion (right topic, wrong direction) — they need different fixes.

---
*Added via Oracle Learn*
