---
title: ## BM25 Routing + Retrieval Architecture Lessons (2026-02-25 to 2026-02-26)
tags: [bm25, faiss, retrieval, eval, anchor, must-contain, routing, thai-legal-rag]
created: 2026-04-14
source: retro: 2026-02-25 to 2026-02-26 BM25 + retrieval anchor + eval suite
---

# ## BM25 Routing + Retrieval Architecture Lessons (2026-02-25 to 2026-02-26)

## BM25 Routing + Retrieval Architecture Lessons (2026-02-25 to 2026-02-26)

**BM25 append-on-load bug**: `BM25Store.__init__` loads existing file, then `add_batch` appends. Every rebuild doubles the corpus unless the old file is wiped first. Fix: check if bm25.pkl exists, unlink before rebuild. A simple count invariant check (should match FAISS metadata count) would catch this immediately.

**BM25-only routing for doc-number queries**: FAISS normalized max=1.0 vs BM25 max=BM25_WEIGHT=0.9 means BM25 can never win in a combined reranker. For doc-number lookups ("กวจ. 5529"), query type detection should route to BM25-only: `r"\b\d{4,}\b"` in `_SPECIFIC_PATTERNS`. FAISS doesn't understand that "5529" is a specific document — it returns semantically similar documents.

**Config vs hardcoded mismatch**: `BM25_WEIGHT=0.9` in config but `"bm25": 0.7` hardcoded in reranker.py. Always import from config, never hardcode weights in the reranker.

**Retrieval Anchor strategy for embedding gaps**: When a chunk has sim < FAISS_TOP_K cutoff, add a short `## บทสรุปสำหรับสืบค้น` anchor section to the MD file. Anchor vocabulary should match query vocabulary directly. sim=0.7307 (miss) → sim=0.8136 (rank 5). Anchor placement matters: putting "ไม่มีอำนาจสั่งการ" before the duty list causes LLM to read duties as constraints.

**must_contain phrases must come from actual LLM output**: Design must_contain from real pipeline runs, not from legal text. A phrase that's legally correct (appears in source document) but the LLM includes non-deterministically should NOT be in must_contain. Options: (1) accept the variance, (2) engineer the retrieval anchor to make the phrase reliably appear in answer.

**Eval suite building methodology**: Collect queries tested ad-hoc across sessions → structure into `golden_test_cases.json` with `must_contain` checks → run `run_eval.py` 3+ times to confirm stability. FAIL on first run may mean wrong phrase in must_contain, not wrong answer.

---
*Added via Oracle Learn*
