# Glossary Expansion Cascade Effect

**Date**: 2026-03-04
**Context**: thai-legal-rag static glossary implementation
**Tags**: rag, query-expansion, glossary, retrieval

## Pattern

Adding a static glossary for query expansion creates cascading regressions when:
1. A query contains multiple glossary keys (e.g. "ค่าปรับ" + "ผ่อนปรน" + "บอกเลิกสัญญา")
2. Each key adds 2-3 expansion terms
3. Combined with Gemini's 5 terms → total queries explodes to 10+
4. Noise overwhelms the original query signal even with ORIGINAL_QUERY_BOOST

## Fix Strategies

- **Trim glossary values**: Only include close synonyms, not loosely related terms
  - Bad: "ผ่อนปรน" → ["ผ่อนผัน", "งดหรือลดค่าปรับ", "ขยายเวลา"] (too broad)
  - Good: "ผ่อนปรน" → ["ผ่อนผัน"] (actual synonym only)
- **Generator rules work**: Adding "always cite numbers/timeframes from docs" fixed a generation-only failure without touching retrieval
- **Global cap needed**: Limit total glossary terms to 2-3 per query regardless of how many keys match

## Key Insight

`key in query` substring matching is greedy — a 30-word query will hit many keys. The glossary should be a precision tool (few, high-confidence synonyms) not a shotgun (every related term).
