---
title: ## Thai Legal RAG Pipeline Implementation Lessons (2026-02-12)
tags: [ocr, pipeline, batch, resume, gemini, google-drive, thai-legal-rag]
created: 2026-04-14
source: retro: 2026-02-12 thai-legal-rag-pipeline
---

# ## Thai Legal RAG Pipeline Implementation Lessons (2026-02-12)

## Thai Legal RAG Pipeline Implementation Lessons (2026-02-12)

**Batch OCR pipeline: build resume/skip logic first**: Always implement resume capability before anything else in a batch processing script — it costs 10 lines and saves hours when things fail mid-run. The `batch_log.csv` approach (track processed files) is simple and reliable.

**Gemini inline_data for OCR**: Gemini's `inline_data` approach (base64 PDF) is simpler than file upload API for small-medium PDFs — no need to manage uploaded file lifecycle.

**Structured output embedded in freeform text is fragile**: Requesting JSON block inside freeform OCR output works but is fragile. For production, use Gemini's `response_mime_type: "application/json"` with a schema.

**Don't trust confidence without empirical testing**: Code written based on documentation and reasoning (no real test data yet) has borrowed confidence. The pipeline was theoretically correct but untested against actual กวจ. PDFs — some field names, OCR quality, and section parsing might need adjustment when real documents arrive.

**Google Drive public URL download is fragile**: The confirmation page workaround is reverse-engineered behavior that Google could change. Using Drive API with service account is more robust for production.

---
*Added via Oracle Learn*
