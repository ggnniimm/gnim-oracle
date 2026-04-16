---
title: ## Generic OCR Prompt for Documents with Attachments
tags: [ocr, gemini, prompt-engineering, attachments, thai-legal]
created: 2026-04-14
source: rrr: gnim-oracle 2026-03-01
---

# ## Generic OCR Prompt for Documents with Attachments

## Generic OCR Prompt for Documents with Attachments

Structured OCR prompts (e.g., "extract ข้อเท็จจริง/ข้อหารือ/ข้อวินิจฉัย") cause LLMs to skip content that doesn't match the expected structure. Documents with attachments (สิ่งที่ส่งมาด้วย) — manuals, templates, wage tables — are silently dropped.

**Solution**: Use generic OCR prompt:
```
คัดลอกข้อความทั้งหมดในเอกสาร PDF นี้ออกมาเป็น Markdown อย่างครบถ้วน
ห้ามสรุป ห้ามตัด ห้ามข้าม — คัดลอก verbatim ทุกหน้า
```
Combined with chunk-based splitting (20 pages per chunk) to prevent Gemini from summarizing long documents.

**Detection heuristic**: chars/page ratio < 50 with page_count > 10 reliably identifies incomplete OCR.

**Impact**: 9 files: 360K → 765K chars total. Some files improved 19-25x.

**Limitation**: Dense numerical tables (wage schedules) may still return 0 chars from Gemini.

---
*Added via Oracle Learn*
