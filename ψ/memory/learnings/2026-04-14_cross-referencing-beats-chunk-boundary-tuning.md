---
title: ## Cross-Referencing Beats Chunk Boundary Tuning
tags: [cross-reference, chunking, retrieval, rag, thai-legal]
created: 2026-04-14
source: Thai Legal RAG TC-042 chunk boundary debugging 2026-03-03
---

# ## Cross-Referencing Beats Chunk Boundary Tuning

## Cross-Referencing Beats Chunk Boundary Tuning

When critical knowledge lives in a document that doesn't rank high enough for a query, don't try to optimize that document's chunks. Instead, add the knowledge as a cross-reference in a document that already ranks well.

**Evidence**: Document 2132 had "ไม่ต้องรอผู้ทิ้งงาน" but ranked 42-85 in FAISS for TC-042 query. Shortening bullets from 538→377 chars actually worsened rank (8→85) because shorter text has less semantic overlap. Adding a one-line cross-ref to document 18077 (rank #1) immediately surfaced the fact in the answer.

**Anti-patterns**:
- Assuming shorter = better for retrieval (shorter text has fewer matching tokens)
- Trying to force a low-ranked document into top-K through text editing alone
- Ignoring the dedup pool cutoff (RERANK_TOP_K × 5) as a hard ceiling

**Notes**: FAISS index at `data/faiss_index/index.faiss` NOT `data/faiss_index.bin`. `rm -f` on non-existent path silently succeeds — always verify after deletion.

---
*Added via Oracle Learn*
