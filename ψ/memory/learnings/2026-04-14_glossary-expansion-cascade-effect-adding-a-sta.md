---
title: ## Glossary Expansion Cascade Effect
tags: [glossary, query-expansion, rag, retrieval, regression]
created: 2026-04-14
source: Thai Legal RAG static glossary implementation 2026-03-04
---

# ## Glossary Expansion Cascade Effect

## Glossary Expansion Cascade Effect

Adding a static glossary for query expansion creates cascading regressions when:
1. Query contains multiple glossary keys (e.g. "ค่าปรับ" + "ผ่อนปรน" + "บอกเลิกสัญญา")
2. Each key adds 2-3 expansion terms
3. Combined with Gemini's 5 terms → total queries explodes to 10+
4. Noise overwhelms original query signal even with ORIGINAL_QUERY_BOOST

**Fix strategies**:
- Trim glossary values: only include close synonyms, not loosely related terms
  - Bad: "ผ่อนปรน" → ["ผ่อนผัน", "งดหรือลดค่าปรับ", "ขยายเวลา"] (too broad)
  - Good: "ผ่อนปรน" → ["ผ่อนผัน"] (actual synonym only)
- Generator rules work for generation-only failures without touching retrieval
- Global cap: limit total glossary terms to 2-3 per query regardless of keys matched

**Key insight**: `key in query` substring matching is greedy. Glossary should be precision tool (few high-confidence synonyms), not shotgun.

---
*Added via Oracle Learn*
