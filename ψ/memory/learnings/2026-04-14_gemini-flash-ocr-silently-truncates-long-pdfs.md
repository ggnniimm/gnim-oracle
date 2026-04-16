---
title: ## Gemini Flash OCR Silently Truncates Long PDFs
tags: [gemini, ocr, truncation, pdf, batch-processing]
created: 2026-04-14
source: Verbatim OCR session 2026-03-21
---

# ## Gemini Flash OCR Silently Truncates Long PDFs

## Gemini Flash OCR Silently Truncates Long PDFs

When OCR'ing a long PDF (16+ pages) with Gemini Flash, the first request may return only ~10 pages despite max_output_tokens=65536 being well above the needed output size. No error — response simply ends mid-document.

**Mitigation**:
1. Always check page count first: `'PDF นี้มีกี่หน้า?'`
2. After OCR, verify last page number in output matches expected total
3. For PDFs >10 pages, consider splitting into two requests (pages 1-N/2, N/2+1-end)
4. Merge parts into single file afterward

Threshold seems to be ~10-12 pages. max_output_tokens is not the bottleneck — Gemini has an internal content generation limit per response.

---
*Added via Oracle Learn*
