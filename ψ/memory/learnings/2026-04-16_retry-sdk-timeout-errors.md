# Retry SDK Timeout Errors

**Date**: 2026-04-16
**Context**: "Stream idle timeout - partial response received" not being retried
**Tags**: #gemini #retry #timeout #resilience

## Problem

`generate_with_retry()` only matched HTTP status codes (`503`, `429`) and gRPC errors (`UNAVAILABLE`, `RESOURCE_EXHAUSTED`). The Gemini SDK error "Stream idle timeout" is a client-side timeout — doesn't contain any of those strings → failed immediately without retry.

## Solution

Case-insensitive matching for: `timeout`, `timed out`, `stream idle` (in addition to existing patterns).

```python
err_lower = err_str.lower()
if any(k in err_lower for k in ("503", "429", "unavailable", "resource_exhausted", "timeout", "timed out", "stream idle")):
```

## Key Insight

SDK client-side errors (timeouts, stream interruptions) are different from server HTTP errors but equally transient. Always test retry conditions against real error messages from production logs, not just documented error codes.

## Files

- `src/gemini_client.py`: retry condition in `generate_with_retry()`
