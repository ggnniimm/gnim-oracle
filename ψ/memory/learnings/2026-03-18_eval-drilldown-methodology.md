---
name: Eval drill-down methodology — 2-3x re-runs to separate retrieval failures from LLM variance
description: Run each failing TC 2-3 times before diagnosing; consistent failures = retrieval gap, intermittent = LLM variance
type: feedback
---

When eval TCs fail, always run each failing TC 2-3 times individually before deciding on a fix strategy. This separates two fundamentally different failure modes:

- **Consistent failure (fails every run)**: The relevant source document is not being retrieved → fix with cross-reference injection into a top-ranked doc
- **Intermittent failure (passes some runs)**: The source IS retrieved but the LLM sometimes omits the specific phrase → fix with must_contain alternatives (array-of-arrays) or accept as known variance

**Why:** In the 2026-03-18 session, 6 TCs failed in the parallel eval run. After drill-down, 4 were LLM variance and only 2 were real retrieval gaps. Without re-runs, we would have wasted time adding cross-refs for problems that don't exist.

**How to apply:** After any eval run with failures, run `--id TC-XXX -v` for each failing TC at least twice. If it passes on re-run, it's LLM variance. If it fails consistently, check the retrieved sources to find which document is missing, then add cross-ref to a consistently top-ranked doc.
