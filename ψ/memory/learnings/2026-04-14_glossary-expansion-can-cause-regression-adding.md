---
title: ## Glossary Expansion Can Cause Regression
tags: [glossary, regression, query-expansion, thai-legal, rag]
created: 2026-04-14
source: rrr: gnim-oracle/thai-legal-rag 2026-03-10
project: github.com/gnim-oracle/thai-legal-rag
---

# ## Glossary Expansion Can Cause Regression

## Glossary Expansion Can Cause Regression

Adding terms to glossary expansion improves target TC but can break unrelated TCs sharing the same trigger keyword.

**Example**: Added "ว ๑๐๘" to `บอกเลิกสัญญา` glossary entry → TC-042 fixed, TC-025 ("การจ้างช่วง") broke because query contained "บอกเลิกสัญญา" and got polluted with irrelevant ว108 chunks.

**Rule**: Before adding glossary terms:
1. Check how many queries in eval contain the trigger keyword
2. Run targeted eval on those queries BEFORE full eval
3. Prefer narrow triggers (multi-word phrases) over broad single keywords

**Also**: CHUNK_SIZE=400 splits bullet lists. If a key phrase is in the last bullet of สรุปข้อวินิจฉัย, it may end up in a separate chunk not reranked into top-K. Fix: move critical phrases to early bullets (within first 400 chars).

---
*Added via Oracle Learn*
