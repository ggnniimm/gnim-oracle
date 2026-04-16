---
name: bidirectional-crossref-for-contrasts
description: When encoding legal distinctions (e.g. ม.97 vs ม.102 authority), add cross-refs to BOTH documents so RAG answers correctly from either direction
type: feedback
---

# Bidirectional Cross-References for Legal Contrasts

When two legal provisions are commonly confused or contrasted (e.g. authority in ม.97 vs ม.102/103), add cross-reference bullets to BOTH source documents, not just one.

**Why:** If cross-ref is only in document A, questions approaching from document B's angle won't surface the distinction. The RAG retrieves different documents depending on query angle. ม.97 queries retrieve ว476; ม.102 queries retrieve doc 61864. Both need the contrast.

**How to apply:** Whenever adding a "ข้อแตกต่างสำคัญ" cross-reference to one document, immediately add the reciprocal cross-reference to the other document(s) involved in the contrast. Then re-index all modified documents and run eval from both query angles.
