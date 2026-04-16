---
title: ## Anchor as Retrieval Guarantee
tags: [retrieval-anchor, must-contain, eval-design, embedding-robustness]
created: 2026-04-14
source: Thai Legal RAG golden eval rebuild 2026-02-26
---

# ## Anchor as Retrieval Guarantee

## Anchor as Retrieval Guarantee

When a legally correct phrase is non-deterministic in LLM output, the fix is to embed the phrase directly into the retrieval anchor — not to lower the test bar.

**Mechanism**: Anchor chunk sits at high cosine similarity (0.81+) to query. When retrieved, its exact text is injected into LLM context. LLM repeats key phrases from high-scoring context.

**Structural placement matters**:
- Phrase at END of bullet → LLM reads as conclusion → tends to repeat
- Phrase BEFORE main content → LLM may treat as constraint/caveat → may summarize away

**Paraphrase robustness test**: Run semantically equivalent queries with different surface forms. If both pull the same document to rank #1, embedding space is finding meaning not just keywords.

**Stability threshold**: 3 runs passing is not sufficient for a phrase that failed even once. Minimum 5 runs; 10+ for statistical confidence. If phrase fails 1/5 runs → treat as non-deterministic → use anchor strategy.

---
*Added via Oracle Learn*
