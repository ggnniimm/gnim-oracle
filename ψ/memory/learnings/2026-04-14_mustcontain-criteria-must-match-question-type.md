---
title: ## must_contain Criteria Must Match Question Type
tags: [eval, must-contain, question-type, thai-legal, test-design]
created: 2026-04-14
source: Thai Legal RAG TC design 2026-03-16
---

# ## must_contain Criteria Must Match Question Type

## must_contain Criteria Must Match Question Type

When writing must_contain for a TC, ask "Would a correct direct answer to THIS question contain this word?" — not "Does the source doc contain this word?"

**Match must_contain to question type**:
- คำถาม "คืออะไร" → definition terms
- คำถาม "ผลเป็นอย่างไร" → consequence terms (ชดใช้, รับผิด)
- คำถาม "ทำอย่างไร" → procedural terms

**Why**: TC-065 "ประมาทเลินเล่ออย่างร้ายแรง คืออะไร" — must_contain had "ชดใช้" (consequence) but question asked for definition. LLM answered definition correctly but test failed because criterion was wrong type.

**How to apply**: Before adding any must_contain, ask "If you answered this question correctly and directly, would you necessarily mention this word?" If unsure, use OR to accommodate legitimate variants.

---
*Added via Oracle Learn*
