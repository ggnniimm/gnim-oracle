---
title: ## Bidirectional Cross-References for Legal Contrasts
tags: [cross-reference, bidirectional, retrieval, thai-legal, rag]
created: 2026-04-14
source: Thai Legal RAG cross-ref design 2026-03-24
---

# ## Bidirectional Cross-References for Legal Contrasts

## Bidirectional Cross-References for Legal Contrasts

When two legal provisions are commonly confused or contrasted (e.g. authority in ม.97 vs ม.102/103), add cross-reference bullets to BOTH source documents, not just one.

**Why**: If cross-ref is only in document A, questions approaching from document B's angle won't surface the distinction. RAG retrieves different documents depending on query angle. ม.97 queries retrieve ว476; ม.102 queries retrieve doc 61864. Both need the contrast.

**How to apply**: Whenever adding a "ข้อแตกต่างสำคัญ" cross-reference to one document, immediately add the reciprocal cross-reference to the other document(s) involved in the contrast. Then re-index all modified documents and run eval from both query angles.

---
*Added via Oracle Learn*
