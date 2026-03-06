# Gemini Stream OCR Can Hang — Always Set Timeout

**Date**: 2026-03-05
**Context**: Batch OCR of 545 OAG PDFs via Gemini Flash `generate_content_stream`

## Problem

Pipeline hung twice at different files (คำวินิจฉัยที่_๑๔๗_๒๕๖๖ and คำวินิจฉัยที่_๑๑๖_๒๕๖๖). The SSE stream connection stayed open but no data came back. No error, no timeout — just silent hang.

## Fix

```python
response = client.models.generate_content_stream(
    model=GEMINI_FLASH_MODEL,
    contents=[prompt, uploaded],
    config=genai_types.GenerateContentConfig(
        http_options={"timeout": 120_000},  # 120s
    ),
)
```

## Rule

Every Gemini API call in a batch pipeline MUST have a timeout. For OCR (which processes the full PDF), 120 seconds is generous enough for large documents but catches genuine hangs.

## Also Learned

- OAG คำวินิจฉัย: 57% procurement-related, 43% other topics (animals, land, criminal, etc.)
- Topic filter at index time (substring match on full text) catches most non-procurement docs
- Pipeline needs periodic FAISS saves, not just at exit — hung pipeline = lost progress

## Tags

`gemini`, `timeout`, `ocr`, `pipeline-reliability`, `batch-processing`
