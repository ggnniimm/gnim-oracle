---
title: ## Check Retrieval Before Adding Cross-Refs
tags: [cross-reference, retrieval, eval, debugging, thai-legal]
created: 2026-04-14
source: Thai Legal RAG session 2026-03-16
---

# ## Check Retrieval Before Adding Cross-Refs

## Check Retrieval Before Adding Cross-Refs

When a TC fails because must_contain keyword isn't found — first verify which documents are ACTUALLY retrieved for the failing query, then add cross-ref to that document.

**Why**: Session 2026-03-16 — added ป.พ.พ. in สรุปข้อวินิจฉัย of อ.100/2564, but that doc wasn't retrieved at all. Query pulled อ.73/2565 instead. Had to fix twice.

**How to apply**: Before editing any document, run `python3 eval/run_eval.py --id TC-XXX --verbose`, check Sources retrieved, then add cross-ref to the top-retrieved doc — not the doc you THINK was retrieved.

---
*Added via Oracle Learn*
