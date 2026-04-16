---
title: ## Anchor-LLM Tension: Retrieval Win ≠ Generation Win
tags: [anchor-llm-tension, retrieval-vs-generation, embedding-dilution, eval-design]
created: 2026-04-14
source: Thai Legal RAG TC-003 × กวจ. 20140 anchor engineering 2026-02-27
---

# ## Anchor-LLM Tension: Retrieval Win ≠ Generation Win

## Anchor-LLM Tension: Retrieval Win ≠ Generation Win

Fundamental tension between anchor text optimized for retrieval vs LLM generation:
- Embedding models reward keyword density — fewer words = less dilution = higher cosine similarity
- LLMs need complete sentences to synthesize meaningful content — keyword lists get ignored

**Evidence**: Keywords-only anchor: retrieval 5/5 ✓, LLM generates phrase 0/10 ✗. Adding just 2 more words dropped retrieval from 5/5 → 2/5.

**Right approach when tension exists**:
1. Don't force the phrase into the broad TC — it will never be stable
2. Create a specific TC with a query that directly targets the document/phrase
3. Accept the trade-off: broad TC gets document as source; specific TC validates phrase content

**Also**: Always test anchor sim with the full stored chunk format (metadata header + content), not just content text. Isolation test ≠ actual FAISS stored vectors.

---
*Added via Oracle Learn*
