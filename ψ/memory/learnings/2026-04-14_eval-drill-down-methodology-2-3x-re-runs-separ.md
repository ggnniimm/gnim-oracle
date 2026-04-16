---
title: ## Eval Drill-Down Methodology: 2-3x Re-Runs Separate Retrieval from Variance
tags: [eval, drill-down, retrieval-failure, llm-variance, methodology]
created: 2026-04-14
source: Thai Legal RAG eval session 2026-03-18
---

# ## Eval Drill-Down Methodology: 2-3x Re-Runs Separate Retrieval from Variance

## Eval Drill-Down Methodology: 2-3x Re-Runs Separate Retrieval from Variance

When eval TCs fail, always run each failing TC 2-3 times individually before deciding on a fix strategy.

- **Consistent failure (fails every run)**: Source document NOT retrieved → fix with cross-reference injection
- **Intermittent failure (passes some runs)**: Source IS retrieved but LLM sometimes omits specific phrase → fix with must_contain alternatives (array-of-arrays) or accept as known variance

**Why**: In 2026-03-18 session, 6 TCs failed. After drill-down: 4 were LLM variance, only 2 were real retrieval gaps. Without re-runs, would have wasted time adding cross-refs for non-existent problems.

**How to apply**: Run `--id TC-XXX -v` for each failing TC at least twice. If it passes on re-run → LLM variance. If consistently fails → check retrieved sources → find missing doc → add cross-ref to consistently top-ranked doc.

---
*Added via Oracle Learn*
