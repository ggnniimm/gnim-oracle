---
title: ## Background Eval: Always Redirect to File, Never Pipe Through tail
tags: [eval, background, pipe-buffering, bash, workflow, thai-legal-rag]
created: 2026-04-14
source: 2026-04-11 learning
---

# ## Background Eval: Always Redirect to File, Never Pipe Through tail

## Background Eval: Always Redirect to File, Never Pipe Through tail

When running eval in background via Bash tool, **never pipe through `tail -N`**:

```bash
# BAD — output file stays 0 bytes until process exits
python3 eval/run_eval.py 2>&1 | tail -20

# GOOD — live output, monitorable with tail -f
python3 eval/run_eval.py > /tmp/eval_out.txt 2>&1 &
```

Also: **always check `ps aux | grep run_eval` before launching a new eval** — stale background processes from previous Bash tool calls may still be running, causing parallel evals and duplicate TC output.

**Why**: The pipe buffers output in memory and only flushes when the writer exits. Combined with `run_in_background`, the output file sees nothing until the whole eval finishes (or never, if background task times out first).

**How to apply**: Every time eval is launched in background, use the redirect pattern. Re-arm Monitor with `tail -f /tmp/eval_out.txt`. Monitor timeout of 360s is too short for a 78-TC eval (~2h) — use persistent: true or re-arm.

---
*Added via Oracle Learn*
