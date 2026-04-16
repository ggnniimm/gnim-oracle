---
title: ## Court Judgment Research, Rescue Phrase Gating, and Lump Sum Knowledge Origin
tags: [rag, ocr, gemini, rescue-phrases, thai-legal-rag, legal-knowledge, gdrive]
created: 2026-04-14
source: Oracle Learn
---

# ## Court Judgment Research, Rescue Phrase Gating, and Lump Sum Knowledge Origin

## Court Judgment Research, Rescue Phrase Gating, and Lump Sum Knowledge Origin

### Context
Thai Legal RAG — court judgment OCR (2026-03-21), GDrive API (2026-03-22), lump sum research (2026-03-24).

### Pattern: Gemini OCR Silently Truncates Long PDFs
First OCR pass may stop at page 10 of 16, or report 374 pages for a 465-page PDF — no error, no warning. Always verify page count with pdfplumber/PyPDF2 after OCR and explicitly request remaining pages.

### Pattern: Rescue Phrases Need Query-Relevance Gating
Rescue phrases fire based on chunk content alone without query context → appends notes about unrelated topics. Fix: use 4-tuple (trigger, phrase, sentence, query_keywords) — only fire when query contains at least one keyword from query_keywords.

### Pattern: Google Drive API Is Available
`src/ingestion/drive.py` has full OAuth2 integration and `stream_pdf(file_id)`. Folder IDs are in `.env`. Always check existing tools before saying "can't access."

### Pattern: Lump Sum vs Unit Price — No Thai Regulation
"เหมารวมใช้เมื่อแบบรูปรายการสมบูรณ์ ปริมาณงานแน่นอน" is FIDIC-derived practitioner knowledge. Thai government documents (พ.ร.บ., ระเบียบ, หลักเกณฑ์ราคากลาง) prescribe HOW to calculate costs and provide templates — they do NOT specify WHEN to use which contract type. Frame as industry practice, not Thai regulation.

### Pattern: Authority Distinction for ม.97 vs ม.102/103
- ม.97 (แก้ไขสัญญา) authority: follows procurement value per ข้อ 165 วรรค 3 — escalates to higher authority when value exceeds head of agency limit
- ม.102 (งดลดค่าปรับ) and ม.103 (บอกเลิกสัญญา) authority: locked to หัวหน้าหน่วยงานของรัฐ per ข้อ 6 — does NOT escalate

Add cross-reference to BOTH ว476 and doc 61864 for bidirectional coverage.

---
*Added via Oracle Learn*
