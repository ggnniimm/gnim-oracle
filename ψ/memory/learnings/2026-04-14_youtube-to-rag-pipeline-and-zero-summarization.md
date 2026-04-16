---
title: ## YouTube-to-RAG Pipeline and Zero Summarization Technique
tags: [rag, knowledge-extraction, zero-summarization, if-then, glossary]
created: 2026-04-14
source: Facebook post on YouTube-to-RAG 2026-03-03
---

# ## YouTube-to-RAG Pipeline and Zero Summarization Technique

## YouTube-to-RAG Pipeline and Zero Summarization Technique

3-step knowledge extraction from YouTube transcripts via NotebookLM:
1. Master outline — "กางสารบัญกลยุทธ์ทั้งหมด ยังไม่ต้องอธิบาย เอาแค่โครงสร้าง"
2. Deep-dive zero summarization — go topic-by-topic: "ห้ามสรุปย่อ เอาแบบละเอียดทุกเม็ด" + force If-Then logic format
3. Glossary — all domain-specific terms with definitions

**Relevance to thai-legal-rag**:
- Zero summarization = generator rule "ห้ามย่อรวมหรือตัดออก"
- If-Then format improves answer actionability: "ถ้าค่าปรับเกิน 10% → ต้องบอกเลิกสัญญา"
- Glossary concept → query expansion / terminology normalization
- Master outline → auto-anchor structure extraction

---
*Added via Oracle Learn*
