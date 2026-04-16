---
title: ## Retrieval Failures vs Generation Failures in RAG
tags: [rag, retrieval-failure, generation-failure, eval, debugging]
created: 2026-04-14
source: rrr: gnim-oracle/thai-legal-rag 2026-03-10
project: github.com/gnim-oracle/thai-legal-rag
---

# ## Retrieval Failures vs Generation Failures in RAG

## Retrieval Failures vs Generation Failures in RAG

When a RAG eval TC fails, diagnose whether it's a retrieval failure (target info NOT in LLM context) or a generation failure (target info IS in context but LLM omits it).

**How to diagnose**:
1. Check which sources were retrieved (eval output shows them)
2. If the document IS retrieved → generation failure
3. If the document is NOT retrieved → retrieval failure

**Fixes**:
- Retrieval failure: cross-reference injection, glossary expansion, query rewriting
- Generation failure: prompt engineering, must-include instructions, or ACCEPT as LLM variance

**Anti-pattern**: Do NOT keep adding cross-references when the right document is already retrieved. Wastes index rebuild time (~10 min) without addressing root cause.

**Rule**: After one rebuild shows right chunks retrieved but TC still failing, STOP retrieval engineering. Check LLM context, then either fix the prompt or accept the variance.

---
*Added via Oracle Learn*
