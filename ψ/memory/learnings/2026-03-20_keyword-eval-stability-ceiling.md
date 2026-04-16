# Keyword Eval Has a Stability Ceiling

**Date**: 2026-03-20
**Context**: Thai Legal RAG eval — 66 TCs, keyword-based must_contain

## Pattern

After fixing all retrieval gaps and obvious LLM paraphrasing issues, keyword-based eval converges to a stability band (64-66/66 = 97-100%). The remaining 2-3% failures come from LLM generating fundamentally different answer *structures* — e.g., listing only examples without stating the principle, or focusing on procedure without mentioning consequences.

## Why It Matters

- Adding more OR alternatives has diminishing returns — at 5+ alternatives per criterion, you're no longer testing for a specific concept
- The failure mode shifts from "wrong word" to "different emphasis" — which keyword matching can't capture
- TC-029 (retrieval variance) and TC-065 (structure variance) represent the two irreducible failure types

## Approaches for the Next Level

1. **Semantic eval**: Compare answer embedding to reference answer (cosine > 0.85 = pass)
2. **LLM-as-judge**: Ask a second LLM if the answer addresses the criterion
3. **Accept the band**: 64-66/66 is excellent for a RAG system — document it as expected behavior
4. **Structure-aware criteria**: Instead of keywords, check for numbered lists or specific section presence

## Tags

eval, LLM-variance, testing-methodology, diminishing-returns
