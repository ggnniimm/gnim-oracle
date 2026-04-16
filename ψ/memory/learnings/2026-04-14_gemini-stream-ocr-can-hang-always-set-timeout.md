---
title: ## Gemini Stream OCR Can Hang — Always Set Timeout
tags: [gemini, timeout, ocr, pipeline-reliability, batch-processing]
created: 2026-04-14
source: Batch OCR of 545 OAG PDFs 2026-03-05
---

# ## Gemini Stream OCR Can Hang — Always Set Timeout

## Gemini Stream OCR Can Hang — Always Set Timeout

Gemini `generate_content_stream` can hang silently — SSE stream connection stays open but no data comes back. No error, no timeout.

```python
response = client.models.generate_content_stream(
    model=GEMINI_FLASH_MODEL,
    contents=[prompt, uploaded],
    config=genai_types.GenerateContentConfig(
        http_options={"timeout": 120_000},  # 120s
    ),
)
```

**Rule**: Every Gemini API call in a batch pipeline MUST have a timeout. For OCR (full PDF processing), 120s is generous enough for large docs but catches genuine hangs.

**Also**: Pipeline needs periodic FAISS saves, not just at exit — hung pipeline = lost progress.

---
*Added via Oracle Learn*
