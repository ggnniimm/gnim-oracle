---
title: Eval/test exit code ≠ success signal — always read SUMMARY section first.
tags: [eval, testing, exit-codes, verification, background-tasks, false-alarms]
created: 2026-04-16
source: rrr: gnim-oracle
---

# Eval/test exit code ≠ success signal — always read SUMMARY section first.

Eval/test exit code ≠ success signal — always read SUMMARY section first.

Test runners exit 1 on any test failure, regardless of how many passed. Background task notifications showing "failed with exit code 1" can mean:
- Eval completed normally with some TCs failing (healthy: e.g. 76/79)
- Or actually crashed mid-run (unhealthy)

The exit code alone can't distinguish these. Always:
1. wc -l + tail output file
2. Look for SUMMARY section (pass/fail counts)
3. Only investigate infrastructure if SUMMARY missing

Concrete case (2026-04-16): Ran thai-legal-rag 79-TC eval, background task reported "failed exit 1". Actual: 76/79 passed, 3 fails including one known-flaky TC-071. Eval worked correctly.

Same pattern applies to linters, type checkers, security scanners — "500 warnings" and "1 error" both trigger exit 1 but are very different situations.

Related: "One failing TC is variance, not regression" — don't react to single data points. LLM variance (2026-03-14) is primary instability source; re-run failing TCs individually before concluding regression.

---
*Added via Oracle Learn*
