---
title: Retry conditions must match SDK error messages, not just HTTP codes. Gemini "Str
tags: [gemini, retry, timeout, resilience, error-handling]
created: 2026-04-16
source: rrr: gnim-oracle-qdrant
---

# Retry conditions must match SDK error messages, not just HTTP codes. Gemini "Str

Retry conditions must match SDK error messages, not just HTTP codes. Gemini "Stream idle timeout" is a client-side SDK error that doesn't contain "503" or "429" — it fell through retry logic and failed immediately. Fix: case-insensitive matching for "timeout", "timed out", "stream idle" in addition to HTTP status codes. Always test retry conditions against real production error strings.

---
*Added via Oracle Learn*
