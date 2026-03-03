# Cross-referencing beats chunk boundary tuning

**Date**: 2026-03-03
**Source**: thai-legal-rag TC-042 chunk boundary debugging
**Tags**: rag, retrieval, chunking, cross-reference, reranking

## Pattern

When critical knowledge lives in a document that doesn't rank high enough for a query, don't try to optimize that document's chunks. Instead, add the knowledge as a cross-reference in a document that already ranks well.

## Evidence

- Document 2132 สรุปข้อวินิจฉัย had "ไม่ต้องรอผู้ทิ้งงาน" but ranked 42-85 in FAISS for TC-042 query
- Shortening bullets from 538→377 chars to fit one chunk actually worsened rank (8→85) because shorter text has less semantic overlap
- Adding a one-line cross-ref to document 18077 (rank #1) immediately surfaced the fact in the answer

## Anti-patterns

- Assuming shorter = better for retrieval (shorter text has fewer matching tokens)
- Trying to force a low-ranked document into top-K through text editing alone
- Ignoring the dedup pool cutoff (`RERANK_TOP_K * 5`) as a hard ceiling

## Related

- FAISS index files live at `data/faiss_index/index.faiss` NOT `data/faiss_index.bin`
- The dedup pool cutoff of 75 items means anything at FAISS rank 76+ is unreachable
- `rm -f` on a non-existent path silently succeeds — always verify after deletion
