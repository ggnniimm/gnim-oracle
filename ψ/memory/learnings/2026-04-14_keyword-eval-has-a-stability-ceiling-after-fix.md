---
title: ## Keyword Eval Has a Stability Ceiling
tags: [eval, keyword-matching, stability-ceiling, llm-variance, testing-methodology]
created: 2026-04-14
source: Thai Legal RAG eval ceiling analysis 2026-03-20
---

# ## Keyword Eval Has a Stability Ceiling

## Keyword Eval Has a Stability Ceiling

After fixing all retrieval gaps and obvious LLM paraphrasing issues, keyword-based eval converges to a stability band (97-100%). The remaining failures come from LLM generating fundamentally different answer structures — listing only examples without stating the principle, or focusing on procedure without mentioning consequences.

**Why it matters**: Adding more OR alternatives has diminishing returns — at 5+ alternatives per criterion, you're no longer testing for a specific concept. Failure mode shifts from "wrong word" to "different emphasis" — which keyword matching can't capture.

**Approaches for next level**:
1. Semantic eval: compare answer embedding to reference answer (cosine > 0.85 = pass)
2. LLM-as-judge: ask a second LLM if the answer addresses the criterion
3. Accept the band: 64-66/66 is excellent — document as expected behavior
4. Structure-aware criteria: check for numbered lists or specific section presence

---
*Added via Oracle Learn*
