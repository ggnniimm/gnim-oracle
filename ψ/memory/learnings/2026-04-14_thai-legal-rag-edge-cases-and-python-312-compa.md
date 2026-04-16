---
title: ## Thai Legal RAG Edge Cases and Python 3.12 Compatibility (2026-02-13)
tags: [python, asyncio, edge-cases, testing, system-prompt, semantic-search, thai-legal-rag]
created: 2026-04-14
source: retro: 2026-02-13 thai-legal-rag-edge-cases
---

# ## Thai Legal RAG Edge Cases and Python 3.12 Compatibility (2026-02-13)

## Thai Legal RAG Edge Cases and Python 3.12 Compatibility (2026-02-13)

**asyncio.coroutine removed in Python 3.11+**: Replace with `async def` function. The pattern was deprecated in 3.8 and removed in 3.11. Can slip through from LightRAG-inspired codebases.

**Test against flat vs nested dict structure**: Chunks from reranker are flat dicts — no nested `metadata` key. Always check actual structure before writing test code.

**Semantic search works cross-language**: FAISS + Gemini embedding can match English queries against Thai documents effectively. No need for Thai-only queries.

**System prompt persona scopes the AI**: "นิติกรชำนาญการพิเศษ" (Senior Legal Officer) persona makes the AI aware of its scope — correctly refuses out-of-scope queries (ผัดไทย recipe, medical questions) and redirects to proper authorities.

**Grep API before trying**: When module structure isn't documented, grep for function names before writing code that guesses the API — saves multiple failed import/call attempts.

**Persistent test files > heredoc one-liners**: Writing test code inline in heredoc loses the test forever. Create `tests/test_edge_cases.py` for persistent coverage.

---
*Added via Oracle Learn*
