# Lesson: Anchor as Retrieval Guarantee

**Date**: 2026-02-26
**Source**: thai-legal-rag golden eval rebuild session

## Pattern

When a legally/factually correct phrase is non-deterministic in LLM output (fails must_contain even once), the fix is not to lower the test bar — it's to embed the phrase directly into the retrieval anchor.

**Wrong approach**: remove the phrase from must_contain because "it's sometimes there"
**Right approach**: update anchor → re-index → verify sim → re-test → add back to must_contain

## Mechanism

The anchor chunk sits at high cosine similarity (0.81+) to the query. When the anchor is retrieved, its exact text is injected into LLM context. The LLM repeats key phrases from high-scoring context. If the phrase is in the anchor at the right structural position, it propagates to the answer reliably.

## Structural placement matters

- Phrase at the END of a bullet point → LLM reads as conclusion, tends to repeat
- Phrase BEFORE the main content → LLM may treat as constraint/caveat, may summarize away
- "โดยผ่านหัวหน้าเจ้าหน้าที่" at end of (2) = conclusion placement → stable

## Paraphrase robustness as free test

Running semantically equivalent queries with different surface forms reveals whether the embedding space is finding meaning vs matching keywords:
- "ครบกำหนดแล้วเสร็จตรงกับวันหยุด" and "สิ้นสุดสัญญาตรงกันวันหยุด" both pull กวจ. 51349 rank #1
- This is a free robustness signal — add paraphrase variants to eval suite when coverage matters

## Stability testing threshold

- 3 runs passing is not sufficient for a phrase that failed even once
- 5 runs is minimum; 10+ is better for statistical confidence
- If a phrase fails in 1/5 runs, treat it as non-deterministic and use anchor strategy

## Tags

`retrieval-anchor`, `must_contain`, `eval-design`, `llm-framing`, `embedding-robustness`
