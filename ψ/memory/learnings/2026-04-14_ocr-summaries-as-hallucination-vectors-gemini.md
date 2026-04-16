---
title: ## OCR Summaries as Hallucination Vectors
tags: [hallucination, ocr, rag, data-quality, thai-legal]
created: 2026-04-14
source: Thai Legal RAG กวจ 22315 data quality 2026-03-04
---

# ## OCR Summaries as Hallucination Vectors

## OCR Summaries as Hallucination Vectors

Gemini-generated บทสรุปสำหรับสืบค้น sections sometimes add interpretive examples not present in the original document. These hallucinated examples get HIGH retrieval scores (perfectly match queries) and get presented as authoritative legal interpretation.

**What happened**: กวจ 22315 ข้อวินิจฉัย discussed post-inspection amendments. Gemini's search summary added examples "เช่น การลดวงเงิน การเพิ่มระยะเวลาส่งมอบ" that aren't in the original document. Gemini inferred them from a different section of law.

**Why dangerous**: 
1. Hallucinated chunk gets high retrieval score
2. Generator trusts chunk content and presents as authoritative
3. No automated eval can catch it — only domain expert

**Fix**: Remove interpretive additions from บทสรุปสำหรับสืบค้น. Rebuild index. Audit all MD files for similar hallucinations.

**Prevention**: Only allow exact quotes from document in search summaries — no interpretation.

---
*Added via Oracle Learn*
