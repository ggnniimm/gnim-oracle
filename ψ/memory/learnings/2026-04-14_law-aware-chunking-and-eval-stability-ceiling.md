---
title: ## Law-Aware Chunking and Eval Stability Ceiling
tags: [rag, eval, chunking, law, thai-legal-rag, stability, qdrant]
created: 2026-04-14
source: Oracle Learn
---

# ## Law-Aware Chunking and Eval Stability Ceiling

## Law-Aware Chunking and Eval Stability Ceiling

### Context
Thai Legal RAG — law-aware chunking (2026-03-18) and eval stabilization (2026-03-19/20).

### Pattern: Law-Aware Chunking Changes Embedding Landscape
Replacing 400-char generic chunks with section-level law chunks (1500+ chars) dilutes keyword density per chunk. Keywords that were concentrated in a 400-char window are now diluted across 1500 chars — changing FAISS retrieval rankings.
**Fix**: Always run eval BEFORE deleting old data. Keep both versions temporarily for A/B comparison.

### Pattern: Law Chunking Scope
Apply section-aware chunking ONLY to primary law files (พ.ร.บ., ระเบียบ, กฎกระทรวง). NOT to ข้อหารือ/คำพิพากษา — those have own structure. Add fallback to generic chunking when law parser finds 0 sections.

### Pattern: Eval Keyword Stability Ceiling
Keyword-based must_contain has a practical ceiling (~96-97% for 66 TCs). Beyond this threshold, failures are LLM generation variance — not retrieval gaps. Strategies at ceiling:
1. OR alternatives for synonym pairs
2. Accept the stability band (e.g., 64-66/66)
3. Switch to semantic eval (cosine similarity) for remaining TCs

### Pattern: OR Alternative Drift Risk
Each TC fix loosens must_contain criteria. At some point (e.g., 5+ alternatives for one concept), the criterion no longer tests meaningful content. Set a threshold: if you need >3 alternatives for one keyword, consider dropping that criterion and testing a different, more stable aspect.

### Pattern: Parallel Eval Workers
With Qdrant server mode, eval can run concurrently. Add `--workers N` flag using `ThreadPoolExecutor`. 3 workers reduces wall time from 22 min to ~8 min for 66 TCs.

### Pattern: Dedup.db Silent Skip
When switching vector stores (local → Docker Qdrant), dedup.db thinks all chunks are already indexed → 0 new chunks, no warning. Must clear dedup.db when switching backends. Add warning when >95% of chunks are skipped.

---
*Added via Oracle Learn*
