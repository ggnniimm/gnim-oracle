# Nuanced Retrieval Over Flat Answers

**Date**: 2026-03-01
**Source**: rrr: thai-legal-rag TC-008

## Pattern

A single edge-case document can transform a wrong flat answer into a correct qualified one. Document 22315 added the เนื้องาน/ไม่เกี่ยวเนื้องาน distinction that changed "ไม่ได้" to "ได้ในบางกรณี" — which is the legally correct answer.

## Concepts

- retrieval-quality
- edge-case-documents
- legal-nuance
- chunk-engineering

## Takeaways

1. **Retrieval quality = nuance coverage**, not just relevance ranking
2. **Indirect citation works**: sources quoted by other documents still influence the answer
3. **Avoid Thai numeral assertions** in must_contain — LLM output is inconsistent between ๙๗ and 97
4. **Fix tooling friction early**: temporary file edits to view full answers should have been a proper flag from the start
