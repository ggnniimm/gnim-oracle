---
title: ## Embedding Gap & Retrieval Anchor Strategy
tags: [embedding-gap, retrieval-anchor, rag, thai-legal, semantic-search]
created: 2026-04-14
source: Thai Legal RAG embedding gap analysis 2026-02-26
---

# ## Embedding Gap & Retrieval Anchor Strategy

## Embedding Gap & Retrieval Anchor Strategy

Embedding gap = distance between query vector and chunk vector that should be relevant but is far apart in embedding space due to:
1. Training data imbalance (model doesn't know Thai legal domain well enough)
2. Corpus imbalance (some concepts have many chunks, others few → embedding space shaped asymmetrically)
3. Vocabulary dilution (chunk has multiple topic clusters → embedding = weighted average → lands in middle, not query cluster)
4. Perspective gap (query is broad/general, chunk is from specific angle)

**Short, focused chunk = dense embedding = better ranking**. Chunk with many topics → embedding is average → doesn't win any cluster.

**Solutions** (by severity):
1. Retrieval anchor: add short ~100 char section using query vocabulary as bridge
2. Increase RERANK_TOP_K (cost: more LLM context noise)
3. Cross-encoder reranker (reads query+chunk together — bypasses embedding space)
4. Query expansion (generate variant queries)

**Anchor section format**: `## บทสรุปสำหรับสืบค้น` in MD source file — indexes as separate chunk.

---
*Added via Oracle Learn*
