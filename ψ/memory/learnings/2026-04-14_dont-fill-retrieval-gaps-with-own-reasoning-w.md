---
title: ## Don't Fill Retrieval Gaps with Own Reasoning
tags: [retrieval-gap, legal-reasoning, thai-legal, rag, hallucination]
created: 2026-04-14
source: Thai Legal RAG กวจ. 5529 session 2026-02-24
---

# ## Don't Fill Retrieval Gaps with Own Reasoning

## Don't Fill Retrieval Gaps with Own Reasoning

When retrieved chunks don't conclusively answer the question, an LLM must NOT fill the gap with its own legal reasoning — even if it seems logical.

**What happened**: Session retrieved chunks about "งดหรือลดค่าปรับ" but กวจ. 5529 wasn't indexed yet. Supplemented with reasoning: "ไม่ได้". This was wrong — when กวจ. 5529 was indexed, it showed the opposite for กรณีที่ 2: "ได้" (under ม. 102 discretion).

**The rule**: When retrieved chunks don't conclusively answer, say "ข้อมูลที่มีไม่เพียงพอในการตอบคำถามนี้" — do NOT substitute with own legal reasoning.

**Why**: Thai legal documents distinguish cases explicitly. A general rule may have exceptions documented only in specific หารือ letters. Without source document, any answer is speculation.

**Document number not searchable**: OCR extracts text but reference numbers in letterheads often get misread. Fix direction: prepend `[doc_number | date | issuer]` to chunk text during indexing.

---
*Added via Oracle Learn*
