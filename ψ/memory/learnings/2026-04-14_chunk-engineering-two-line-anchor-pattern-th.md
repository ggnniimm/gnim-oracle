---
title: ## Chunk Engineering — Two-Line Anchor Pattern
tags: [chunk-engineering, anchor-design, llm-framing, retrieval]
created: 2026-04-14
source: Thai Legal RAG chunk engineering 2026-02-27
---

# ## Chunk Engineering — Two-Line Anchor Pattern

## Chunk Engineering — Two-Line Anchor Pattern

The `## บทสรุปสำหรับสืบค้น` section in MD source files serves dual purpose:
1. Retrieval anchor: FAISS indexes as a chunk; keyword density determines sim score
2. LLM framing: text shapes how LLM interprets and presents document content

**Two-line recipe**:
```
Line 1: keyword-dense anchor (for retrieval)  
Line 2+: framing sentence (for LLM interpretation)
```

| Anchor type | Sim score | Retrieval | LLM quality |
|---|---|---|---|
| Keywords only | 0.79-0.80 | Excellent | Poor |
| Full sentence only | 0.73-0.76 | Often fails | Good when retrieved |
| Keywords + sentence below | 0.79-0.80 | Excellent | Good |

Trick: FAISS embeds whole chunk, but keyword-dense first line dominates the embedding. Sentence below adds context for LLM without significantly diluting the vector.

**Danger**: This is editorial power — you're changing how the summary presents content without changing the law. Only use when framing is defensible.

---
*Added via Oracle Learn*
