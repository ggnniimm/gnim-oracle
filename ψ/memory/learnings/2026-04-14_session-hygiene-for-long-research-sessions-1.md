---
title: ## Session Hygiene for Long Research Sessions
tags: [session-hygiene, checkpointing, experiment-logging, retrospective]
created: 2026-04-14
source: Full-day dig retrospective 2026-02-12
---

# ## Session Hygiene for Long Research Sessions

## Session Hygiene for Long Research Sessions

1. **Experiment files need context notes**: Any file committed to `ψ/lab/` needs context — commit message, README, or first comment explaining the experiment. Without this, artifacts are archaeologically opaque 3 months later.

2. **Long sessions need checkpoints**: Sessions >2 hours covering multiple topics risk context drift. Rule: `/forward` at every major topic transition, not just end of day. Good transitions: end of "research" before "implementation", after deep-diving one codebase before another, after completing a deliverable.

3. **Every session deserves a retrospective**: Even infrastructure sessions contain decisions about tool design, patterns about what tools Ming actually uses, and friction points worth capturing.

4. **`/rrr --dig` as reconstruction tool**: Can reconstruct day's work from .jsonl session files even without real-time /rrr. Limitation: can't recover the "why" of decisions — only the "what".

---
*Added via Oracle Learn*
