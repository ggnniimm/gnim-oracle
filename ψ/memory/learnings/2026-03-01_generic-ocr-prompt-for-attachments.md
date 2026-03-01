# Generic OCR Prompt for Documents with Attachments

**Date**: 2026-03-01
**Source**: rrr: gnim-oracle
**Concepts**: ocr, gemini, prompt-engineering, thai-legal-rag, attachments

## Pattern

Structured OCR prompts (e.g., "extract ข้อเท็จจริง/ข้อหารือ/ข้อวินิจฉัย") cause LLMs to skip content that doesn't match the expected structure. Documents with attachments (สิ่งที่ส่งมาด้วย) like manuals, templates, wage tables, and operational guidelines are silently dropped.

## Solution

Use a generic OCR prompt for heterogeneous documents:
```
คัดลอกข้อความทั้งหมดในเอกสาร PDF นี้ออกมาเป็น Markdown อย่างครบถ้วน
ห้ามสรุป ห้ามตัด ห้ามข้าม — คัดลอก verbatim ทุกหน้า
```

Combined with chunk-based splitting (20 pages per chunk) to prevent Gemini from summarizing long documents.

## Detection Heuristic

chars/page ratio < 50 with page_count > 10 reliably identifies incomplete OCR.

## Impact

9 files: 360K → 765K chars total. Some files improved 19-25x (3K → 66K for 77-page document).

## Limitation

Dense numerical tables (e.g., wage schedules) may still return 0 chars from Gemini — no good workaround yet.
