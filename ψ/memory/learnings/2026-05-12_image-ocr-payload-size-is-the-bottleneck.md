# Image OCR: payload size dominates per-call latency, not rate limits

**Date**: 2026-05-12
**Source**: batch 4 cleanup, gnim-oracle thai-legal-rag re-OCR

## The Lesson

When per-page Gemini OCR calls time out at 300 DPI on large image scans (3-5 MB
PNG), the bottleneck is **upload payload size**, not rate limits or model
latency. Falling back to 200 DPI (44% the bytes) recovers ~100% of stuck pages
in a single retry.

## How we learned it

Batch 4 OCR (14 หนังสือเวียน, flash→Pro upgrade) left 133 placeholder pages
across 10 MDs marked `quality: low`.

**Attempt 1** — retry at 300 DPI with 300s per-page timeout:
- Ran 5.5h, recovered 85/133 (64%)
- 48 pages stuck — every stubborn one was 3-5 MB at 300 DPI
- Hypothesis: rate-limited / "stubborn page content"

**Attempt 2** — retry the same 48 pages at 200 DPI:
- Ran 1.5h, recovered **48/48 (100%)**
- Each page completed in 30-90s (well inside the 300s window)
- Hypothesis falsified: not about rate limits, about upload bytes

## Why 200 DPI works

- 200²/300² ≈ 0.44 → ~56% payload reduction
- Smaller upload finishes inside the per-call timeout window
- OCR accuracy on 200 DPI legal docs is still excellent (Gemini 2.5 Pro handles it cleanly)

## The durable fix (commit `1cdc1dc`)

`ψ/lab/thai-legal-rag/src/ingestion/ocr.py` per-page extract path now tries
300 DPI first; on timeout/error, single-page re-renders at 200 DPI and retries
once before recording a placeholder.

- Keeps 300 DPI as default (quality on the happy path)
- Pays the re-render cost only on failures
- Added `_pdf_page_to_image(pdf_bytes, page_idx, dpi)` helper (single-page render, no whole-PDF reprocess)

## Adjacent insight

I almost missed this because the surface symptoms (429s, slow calls) fit the
"rate limit" hypothesis. They *also* fit "upload too slow" — but "upload size
dominates" additionally explains the pure ReadTimeouts that had no 429
attached. **Test the alternative hypothesis even when the primary fits.**

## What this changes going forward

- Don't lower default DPI globally — preserve quality on the happy path
- Don't assume "rate-limited" from timeouts alone — measure upload time
- Same pattern likely applies to other image-API calls (Vision API, Anthropic with images, etc.)

## Related

- [[2026-05-10_streaming-api-200ok-not-success-and-retry-granularity]] — also about misattributing failures (streaming 200 OK ≠ success)
- [[feedback_verify-before-act]] — diagnose before fixing
