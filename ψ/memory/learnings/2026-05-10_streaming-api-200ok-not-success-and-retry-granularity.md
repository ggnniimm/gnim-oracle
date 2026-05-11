---
name: Streaming API — 200 OK ≠ success + retry granularity
description: Vertex AI streaming 200 OK is just connection start; failure happens mid-stream. Retry granularity should match failure scope.
type: project
---

## Lesson 1: 200 OK ≠ success in streaming APIs

`generate_content_stream` on Vertex AI returns HTTP 200 OK when the streaming connection opens. The actual content arrives as SSE events. A 429 RESOURCE_EXHAUSTED can appear mid-stream (at ~80s for a 71-page structured output), after the 200 OK.

**Symptom**: log shows `"HTTP/1.1 200 OK"` then 80+ seconds later `attempt N failed: 429`.

**Why:** The model starts generating output. Midway through the long response, the per-minute token budget is exhausted and an error event is emitted in the stream. The SDK converts it to an exception during `for chunk in response:` iteration.

**Fix:** Wrap stream iteration in try/except with retry, separate from the initial call. Or prefer non-streaming `generate_content` for very large outputs (loses streaming latency but avoids mid-stream failure).

## Lesson 2: Raw cache must be read, not just written

Checkpoint files written after each step are useless if the retry logic doesn't load them. Pattern: always implement resume alongside the checkpoint write.

```python
# WRONG: write-only checkpoint
raw_cache.write_text(json.dumps(raw_pages), ...)  # saves, but never loaded on retry

# RIGHT: write + resume
if raw_cache.exists():
    cached = json.loads(raw_cache.read_text())
    raw_pages = cached
    start_page = len(cached)
# then loop from start_page onwards
```

## Lesson 3: Retry granularity should match failure scope

Retrying the whole OCR pipeline (classify + extract + structure + anchor) when only the anchor fails is over-retry. It re-extracts 71 pages unnecessarily.

**Rule:** retry at the smallest scope that makes the operation idempotent:
- anchor fail (non-fatal) → return "" and continue, don't retry whole file
- structure fail → retry structure call only (cache gives free re-entry)
- page extract fail → placeholder and continue to next page

**Why:** `ocr_with_retry` in reocr_circulars_pro.py wraps the whole `pdf_to_markdown()` call. When anchor raises, it propagates up and triggers a full-file retry. Should be: anchor catches all exceptions internally (already does), structure should catch + retry internally too.
