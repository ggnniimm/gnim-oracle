---
title: ## stdout Buffering Looks Like a Deadlock
tags: [stdout-buffering, debugging, python, deadlock, performance]
created: 2026-04-14
source: Thai Legal RAG eval hang investigation 2026-03-04
---

# ## stdout Buffering Looks Like a Deadlock

## stdout Buffering Looks Like a Deadlock

When running Python scripts in background with output redirected to file, `print()` output is block-buffered — doesn't appear until buffer fills or program exits. A script that prints "Loading..." then spends 15 minutes on API calls will show ONLY "Loading..." the entire time — looks exactly like a hang.

**Fix**:
```bash
PYTHONUNBUFFERED=1 python3 script.py 2>&1
# or
python3 -u script.py 2>&1
```

**Diagnostic technique**: Isolate suspected hanging operation:
```python
python3 -c "from module import Thing; Thing()"
```
If completes instantly → original script isn't stuck, just not flushing.

**Key lesson**: Before diagnosing deadlocks/race conditions — first verify process is actually stuck. CPU 0% alone is not proof (could be waiting on network I/O). Run `ps`, isolate components to test independently.

---
*Added via Oracle Learn*
