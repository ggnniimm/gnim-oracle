# Retrieval Failures vs Generation Failures in RAG

**Date**: 2026-03-10
**Source**: rrr: gnim-oracle/thai-legal-rag
**Confidence**: High (confirmed across TC-042, TC-035, TC-037)

## Pattern

When a RAG eval TC fails, diagnose whether it's a **retrieval failure** (target info not in LLM context) or a **generation failure** (target info IS in context but LLM omits it from answer).

## How to Diagnose

1. Check which sources were retrieved (eval output shows them)
2. If the document containing the expected phrase IS retrieved → generation failure
3. If the document is NOT retrieved → retrieval failure

## Fixes

- **Retrieval failure**: Cross-reference injection, glossary expansion, query rewriting
- **Generation failure**: Prompt engineering, must-include instructions, or **accept as LLM variance**

## Anti-pattern

Do NOT keep adding cross-references to more documents when the right document is already retrieved. This wastes index rebuild time (~10 min each) without addressing the root cause.

## Example

TC-042: "ไม่ต้องรอ" — document 11886 with cross-reference was retrieved, but LLM chose not to output the specific phrase. Three index rebuilds wasted before accepting this as generation variance.

## Rule

After one rebuild shows the right chunks retrieved but TC still failing, STOP retrieval engineering. Check the LLM context, then either fix the prompt or accept the variance.
