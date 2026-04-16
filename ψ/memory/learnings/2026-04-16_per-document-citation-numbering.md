# Per-Document Citation Numbering

**Date**: 2026-04-16
**Context**: User reported `[2], [2], [3], [3], [3], [5], [5]` in RAG answers
**Tags**: #generator #citation #rag #ux

## Problem

`build_context()` assigned sequential numbers to each chunk: if document A had 3 chunks, they got [2], [3], [4]. The LLM then cited each chunk number individually when referencing document A, creating noisy repeated citations like `[2], [2], [3], [3], [3]`.

## Solution

1. **Per-document numbering**: Group chunks by `source_name`, assign one number per document. All chunks from the same document are combined under a single `[N]` header.
2. **Prompt rule**: Added "ห้ามเขียนเลขอ้างอิงซ้ำติดกัน เช่น [2], [2], [3], [3] ผิด ให้เขียน [2], [3] เพียงครั้งเดียว"

## Key Insight

The LLM was technically correct — it cited the chunk numbers it was given. The fix was to give it one number per document, not per chunk. Prompt rule is belt-and-suspenders defense.

## Files

- `src/generation/generator.py`: `build_context()` rewritten to group by source_name
