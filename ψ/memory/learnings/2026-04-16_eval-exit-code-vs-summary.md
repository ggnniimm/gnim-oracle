# Eval Exit Code ≠ Success Signal — Always Read SUMMARY Section

**Date**: 2026-04-16
**Context**: 79-TC eval run after PR #19. Background task notification reported `<status>failed</status>` with exit 1. Actual result: 76/79 passed (healthy).
**Tags**: #eval #testing #exit-codes #verification

## Problem

Test runners / eval scripts often exit with code 1 when *any* test case fails, regardless of how many passed. When the task runner reports "failed with exit code 1," the instinct is to interpret that as broken or crashed. It's not — it's the normal exit behavior for any test run with failures.

If I react to the exit code instead of the actual output, I'll:
- Assume the eval crashed or couldn't produce results
- Spiral into debugging infrastructure instead of reading the report
- Miss that 76/79 is a healthy baseline

## Specific Case

Today I ran `python3 eval/run_eval.py --workers 3` in the background. The task notification came back:

```
<status>failed</status>
<summary>Background command "Run eval 79 TCs in background with 3 workers" failed with exit code 1</summary>
```

My first read: "something broke." Then I checked `/tmp/eval_out.txt` and saw the SUMMARY clearly:

```
SUMMARY  76/79 passed
Failed cases:
  ✗ TC-027 ...
  ✗ TC-037 ...
  ✗ TC-071 ...  (known flaky)
```

Eval finished correctly. The exit 1 was because 3 TCs failed assertions — expected behavior.

## Solution

**For test suites / evals, always read the output summary, not the exit code.**

Sequence:
1. Background task reports failed/exit-1 — treat as "needs investigation," not "broken"
2. `wc -l` + `tail -50` the output file
3. Look for SUMMARY section first (pass/fail counts, failed case list)
4. Only if SUMMARY is missing or output is truncated → then investigate infrastructure

For my own scripts going forward, two options:
- Add `--summary-exit-0` flag so CI-like exit semantics don't mask healthy runs
- Or accept the convention and always check output

## Key Insight

Exit codes are designed for CI pipelines ("block merge if any test fails"). They're binary — and for a human operator scanning results, that binary hides the signal. **Read the diff of passes vs fails, not the return code.** Same pattern for linters, type checkers, security scans — they all exit non-zero on findings, but "500 warnings" and "1 error" are very different situations that exit code 1 collapses into one.

Related: when a user reports a bug, verify the *observed state* before reacting (2026-04-16 earlier learning). Same principle — treat signals as hypotheses, not facts.

## Files

- No code files — this is a process/interpretation learning
