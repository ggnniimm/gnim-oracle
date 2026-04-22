---
title: Document structure does not prove content provenance in Thai legal RAG.
tags: [provenance, cross-ref, ocr, thai-legal-rag, verification, pdf]
created: 2026-04-18
source: rrr: gnim-oracle-qdrant
---

# Document structure does not prove content provenance in Thai legal RAG.

Document structure does not prove content provenance in Thai legal RAG.

When verifying whether text in an OCR-generated MD file is original or injected cross-ref, section name alone is not evidence. Text in `## ข้อวินิจฉัย` COULD be original but may also have been injected there.

Verification chain: (1) git history if file is tracked, (2) source PDF. If Drive MCP unavailable, suggest `! open "https://drive.google.com/file/d/<id>/view"` for user to verify directly.

Never answer provenance questions from structure alone — always go to source.

---
*Added via Oracle Learn*
