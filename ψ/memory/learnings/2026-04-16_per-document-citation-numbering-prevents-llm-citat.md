---
title: Per-document citation numbering prevents LLM citation spam. When build_context()
tags: [rag, citation, generator, ux, prompt-engineering]
created: 2026-04-16
source: rrr: gnim-oracle-qdrant
---

# Per-document citation numbering prevents LLM citation spam. When build_context()

Per-document citation numbering prevents LLM citation spam. When build_context() assigns sequential numbers to each chunk, the same document with 3 chunks gets [2], [3], [4] — and the LLM cites all three, creating noisy [2], [2], [3], [3], [3] output. Fix: group chunks by source_name, assign one number per document. Combined with prompt rule "ห้ามเขียนเลขอ้างอิงซ้ำติดกัน" as defense-in-depth.

---
*Added via Oracle Learn*
