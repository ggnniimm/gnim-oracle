---
title: ## Rescue Phrases, FAISS_TOP_K Headroom, and Cross-Reference Target Selection
tags: [rag, retrieval, rescue-phrases, cross-reference, chunk-engineering, thai-legal-rag]
created: 2026-04-14
source: Oracle Learn
---

# ## Rescue Phrases, FAISS_TOP_K Headroom, and Cross-Reference Target Selection

## Rescue Phrases, FAISS_TOP_K Headroom, and Cross-Reference Target Selection

### Context
Thai Legal RAG — TC-042/TC-003 final fixes. Rescue phrase mechanism and top-K tuning.

### Pattern: Rescue Phrases as Post-Processing Safety Net
When retrieval works but LLM paraphrases away critical legal terminology:
```python
_rescue_key_phrases = [
    ("trigger_phrase_in_chunks", "phrase_to_append_if_missing"),
]
```
Scan retrieved chunks for trigger phrase. If present but missing from answer, append note. 3 rescue phrases is fine; 10+ needs rethinking.

### Pattern: FAISS_TOP_K Headroom
Doubling from 40→80 brought in documents at ranks 49-74 that were critical for specific queries. The reranker (MMR) still filters to 15 — more candidates = better selection without degrading quality.

### Pattern: Cross-Reference Must Target Consistently Top-Ranked Document
Before injecting cross-ref content, always verify which document ACTUALLY gets retrieved for the query (run pipeline diagnostics). Target the doc that consistently reaches rank 1, not just "a relevant doc."

First attempt in ว52 failed because ว52 wasn't top-ranked for TC-050 — ว647 was. Verify → target → inject.

### Pattern: LLM Position Effect
Moving critical content to **first bullet with bold** in สรุปข้อวินิจฉัย consistently outperforms having the same content in later bullets. LLM anchors on opening statements.

### Pattern: Adding Text Changes Chunk Boundaries
Adding ~50 words of cross-ref text to a large document shifts where CHUNK_SIZE splits occur. This can cause unrelated TCs to regress if a previously-in-chunk phrase now falls into the next chunk. Always run full eval after cross-ref injection.

---
*Added via Oracle Learn*
