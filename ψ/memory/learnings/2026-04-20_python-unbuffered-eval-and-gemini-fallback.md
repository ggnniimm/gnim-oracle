# Lesson: Python -u + Gemini fallback chain for eval resilience

**Date**: 2026-04-20
**Context**: Full eval (78 TCs) appeared hung for 30 min — actually 2 separate issues compounding

## What happened

Started full eval in background, saw 0 TCs complete after 30 min despite process at 94% CPU. Assumed Gemini 503. Expanded fallback chain in `gemini_client.py`. Restarted. Still "hung."

`lsof -p $PID` revealed: fd 1 (stdout) was a regular REG file, not CHR tty → Python block-buffered it at 4KB. `print_result()` output was sitting in buffer, never flushing to file. Retry logs came through because `logger.warning` uses stderr which flushes.

## Fix

**1. `python3 -u eval/run_eval.py ...`** → unbuffered stdout, TC results appear realtime.

**2. Fallback chain** (kept — separate improvement):
```python
_FALLBACK_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",  # different alias, routes to different backend pool
]
# DO NOT add gemini-2.0-flash or 2.0-flash-lite — both return 404 (deprecated)
```

**3. Round-2 cooldown**: after full chain fails once, sleep 20s + jitter and retry all models once more. Google infra 503 typically recovers in 30-60s.

**4. `ThreadPoolExecutor.shutdown(wait=False)`** for per-TC timeout:
```python
_pool = ThreadPoolExecutor(max_workers=1)
_future = _pool.submit(run_case, case, retriever, generate)
try:
    result = _future.result(timeout=tc_timeout)
except FuturesTimeout:
    _future.cancel()
    result = {"passed": None, "warnings": [f"timeout after {tc_timeout}s"]}
finally:
    _pool.shutdown(wait=False)  # don't block main loop waiting for stuck thread
```

`with ThreadPoolExecutor(...)` context manager blocks on exit — can't use it for true timeout.

## Why it matters

Before this session: eval would hang silently on Gemini 503, requiring manual kill. No way to tell if API was actually down vs eval bug.

After: timeout marks TC as SKIP after 180s, eval continues. Fallback chain tries 3 models × 2 rounds before giving up. Unbuffered output shows progress as each TC completes.

## Diagnostic pattern

When background process "hung but CPU active":
1. `ps -p $PID -o etime,stat,%cpu` — confirm still running
2. `lsof -p $PID | grep -E "REG|CHR|PIPE"` — check stdout fd type
3. `stat -f %m /output/file` vs `date +%s` — is file being updated?
4. If stdout is REG (file) not CHR (tty) → **Python block-buffers**. Fix: `python3 -u`.

## Concepts
python, buffering, eval, gemini, retry, timeout, thread-pool, debugging
