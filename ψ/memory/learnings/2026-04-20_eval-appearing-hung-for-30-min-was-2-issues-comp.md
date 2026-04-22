---
title: Eval appearing "hung" for 30 min was 2 issues compounding: (1) Python stdout blo
tags: [python, buffering, eval, gemini, retry, timeout, thread-pool, debugging, rag]
created: 2026-04-20
source: rrr: gnim-oracle-qdrant
---

# Eval appearing "hung" for 30 min was 2 issues compounding: (1) Python stdout blo

Eval appearing "hung" for 30 min was 2 issues compounding: (1) Python stdout block-buffered to 4KB when redirected to file (not tty) — fix with `python3 -u`; (2) Gemini 503 transient — fix with expanded fallback chain (2.5-flash → 2.5-flash-lite → flash-latest, DO NOT use 2.0-flash which is 404 deprecated) + round-2 cooldown after full chain fails. Diagnostic pattern: `lsof -p $PID | grep -E "REG|CHR"` — if stdout fd is REG (file) not CHR (tty), Python block-buffers. Also: `ThreadPoolExecutor.shutdown(wait=False)` is the correct way to implement per-TC timeout without blocking main loop; the `with` context manager waits for stuck threads.

---
*Added via Oracle Learn*
