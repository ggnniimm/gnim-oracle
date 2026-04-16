---
title: ## OCR Batch Pipeline Design Lessons
tags: [ocr, batch-pipeline, gemini, google-drive, rag, thai-legal, metadata]
created: 2026-04-14
source: Thai Legal RAG Pipeline 2026-02-12
---

# ## OCR Batch Pipeline Design Lessons

## OCR Batch Pipeline Design Lessons

1. **Resume logic is non-negotiable**: Build skip-already-processed logic first. Log each success to CSV immediately after it happens. On restart, read log and skip completed items.

2. **Gemini inline_data for PDFs**: For PDFs ≤ few MB, base64 inline_data is simpler than file upload API — no upload lifecycle management needed.

3. **Structured output in freeform = fragile**: Use `generation_config={"response_mime_type": "application/json", "response_schema": {...}}` for metadata extraction. Two-call approach (OCR first, extract second) is more reliable than one-call hybrid.

4. **Google Drive public URL**: `https://drive.google.com/uc?export=download&id=FILE_ID`. Check first 4 bytes == `b'%PDF'` to verify actual PDF received.

5. **YAML frontmatter schema for Thai legal RAG**: Key fields: `doc_type`, `issued_by`, `doc_number`, `date_be`, `laws_referenced`, `sections_referenced`, `source_drive`, `quality`, `status`.

---
*Added via Oracle Learn*
