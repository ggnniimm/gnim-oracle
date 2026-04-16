---
title: ## Payload Filter Architecture and RAG Eval Deep Review
tags: [qdrant, rag, filter, eval, thai-legal-rag, architecture]
created: 2026-04-14
source: Oracle Learn
---

# ## Payload Filter Architecture and RAG Eval Deep Review

## Payload Filter Architecture and RAG Eval Deep Review

### Context
Thai Legal RAG — payload filter (2026-03-25/26/27/28), eval review.

### Pattern: Query Qdrant Payload Before Writing Filter Code
Before writing any filter (`FieldCondition`), curl the actual payload to confirm field names:
```bash
curl http://localhost:6333/collections/thai_legal/points/scroll -d '{"limit": 1}'
```
`doc_type` in source code ≠ `category` in Qdrant payload (md_loader silently remaps). Silent 0-results from wrong field name wastes rebuild cycles.

### Pattern: Payload Filter as Generic Dict
```python
payload_filter: dict = {"field": "category", "value": "คำพิพากษาศาลปกครอง"}
# or
payload_filter: dict = {"field": "issued_by", "value": "สำนักงานอัยการสูงสุด"}
```
Generalize to `{field, value}` so any Qdrant payload field can be filtered without code changes. Don't hardcode field names as function params.

### Pattern: History-Aware Intent Detection
Scan last 6 user messages for filter-triggering keywords. Follow-up queries ("แล้วเรื่องนี้มั้ย") don't repeat original keywords but should inherit the filter. Risk: over-persistence — if user switches topic, filter stays for 6 turns. Consider capping at 3 turns.

### Pattern: must_contain Answer-Direction Review
For yes/no questions, must_contain MUST include the answer direction (ไม่ต้องรอ, ไม่อาจ, ได้, มีสิทธิ). Without it, a wrong answer with correct keywords passes.
After model upgrades, review must_contain for criteria that matched old model's phrasing rather than actual answer content.

### Pattern: Single Source of Truth for Vector DB
Don't maintain parallel Qdrant instances (embedded + server). Use one, expose via port, point ALL consumers (eval, web app, CLI) at it. Eval on one DB, web app on another = silent divergence.

---
*Added via Oracle Learn*
