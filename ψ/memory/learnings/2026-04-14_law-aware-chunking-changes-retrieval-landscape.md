---
title: ## Law-Aware Chunking Changes Retrieval Landscape — Run Eval Before Deleting Old
tags: [chunking, retrieval, embedding, thai-legal, eval]
created: 2026-04-14
source: Thai Legal RAG law-aware chunking 2026-03-18
---

# ## Law-Aware Chunking Changes Retrieval Landscape — Run Eval Before Deleting Old

## Law-Aware Chunking Changes Retrieval Landscape — Run Eval Before Deleting Old Data

Switching from generic 400-char chunks to section-aware chunks (มาตรา/ข้อ level) changes the embedding landscape. Bigger chunks dilute keyword density — a keyword prominent in a 400-char window gets buried in a 1500-char section chunk.

**Why**: TC-001 regressed because old ระเบียบ.pdf generic chunks had "ความสัมพันธ์" in a focused 400-char window → high similarity. After law-aware chunking, that keyword is embedded within a large section chunk → lower similarity.

**How to apply**:
1. Always run eval BEFORE deleting old vector data — keep both versions for A/B comparison
2. When changing chunk strategy, budget time for per-TC regression analysis
3. `--force-reindex --file` should search by file stem (not exact source_name) to handle `.pdf` → `.md` transitions
4. Consider keeping small keyword-rich "anchor" chunks alongside section-aware chunks for better recall on keyword-heavy queries

---
*Added via Oracle Learn*
