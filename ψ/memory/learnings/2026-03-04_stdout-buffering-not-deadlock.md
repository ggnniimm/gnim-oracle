# stdout Buffering Looks Like a Deadlock

**Date**: 2026-03-04
**Context**: thai-legal-rag eval runs appearing to hang at "Loading index..."
**Tags**: debugging, stdout, buffering, python

## Pattern

When running Python scripts in the background with output redirected to a file, `print()` output is **block-buffered** (not line-buffered). This means output doesn't appear in the file until the buffer fills up or the program exits.

A long-running script that prints "Loading..." then spends 15 minutes on API calls will show ONLY "Loading..." in the output file the entire time — looking exactly like a hang/deadlock.

## Misdiagnosis Chain

1. "FAISS file locking" — wrong, processes were reading different files
2. "RAM exhaustion" — wrong, 16GB was tight but not the cause
3. "Python 3.14 no-GIL deadlock" — wrong, `PYTHON_GIL=1` didn't help
4. **Actual cause**: stdout buffering when redirected to file

## Fix

```bash
PYTHONUNBUFFERED=1 python3 script.py 2>&1
# or
python3 -u script.py 2>&1
```

## Diagnostic Technique

Isolate the suspected hanging operation in a standalone script:
```python
python3 -c "from module import Thing; Thing()"
```
If it completes instantly, the original script isn't stuck — it's just not flushing output.

## Key Lesson

Before diagnosing deadlocks, race conditions, or resource contention — first verify the process is actually stuck (`CPU 0%` alone is not proof; it could be waiting on network I/O). Run `ps` to check CPU, and isolate components to test independently.
