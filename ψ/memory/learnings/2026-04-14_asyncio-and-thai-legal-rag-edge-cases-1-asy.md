---
title: ## asyncio and Thai Legal RAG Edge Cases
tags: [asyncio, python, reranker, gemini, embedding, thai-legal]
created: 2026-04-14
source: Thai Legal RAG edge case testing 2026-02-13
---

# ## asyncio and Thai Legal RAG Edge Cases

## asyncio and Thai Legal RAG Edge Cases

1. **asyncio.coroutine removed in Python 3.11** (not 3.12): Use `async def _empty_coroutine(): return []` instead.

2. **Reranker chunks are flat dicts**: Chunks from `rerank()` in `src/retrieval/reranker.py` have no nested `metadata` key — use `chunk.get('source_name', '')` not `chunk['metadata']['source_name']`.

3. **Gemini embedding is multilingual**: `gemini-embedding-001` can match English queries against Thai documents without translation.

4. **System prompt persona = scope guard**: Giving LLM a specific persona ("นิติกรชำนาญการพิเศษ") helps it reject irrelevant queries politely and request clarification — better than explicit "if unrelated, say X" rules.

5. **Grep API before testing**: When unsure about self-written module API, `grep "^def \|^class "` the file first — faster than fixing ImportError repeatedly.

---
*Added via Oracle Learn*
