---
title: ## must_contain Must Check Answer Direction for Yes/No Questions
tags: [eval, must-contain, answer-direction, yes-no, thai-legal]
created: 2026-04-14
source: Thai Legal RAG eval TC-043/044 design 2026-03-25
---

# ## must_contain Must Check Answer Direction for Yes/No Questions

## must_contain Must Check Answer Direction for Yes/No Questions

For yes/no questions ("ต้องรอมั้ย", "เพิ่มค่างานได้มั้ย"), must_contain must include the affirmative/negative word indicating correct answer direction. Otherwise a factually wrong answer containing the right keywords will still pass.

**Why**: TC-043 "ต้องรอผลพิจารณาผู้ทิ้งงานก่อนหรือไม่" — correct answer is "ไม่ต้องรอ". But must_contain only had ["ผู้รับจ้างรายใหม่", "ผู้ทิ้งงาน"] — would pass even if answer said "ต้องรอ".

**How to apply**: Include answer direction criterion:
- "ไม่ต้องรอ" for "ต้องรอมั้ย → ไม่ต้อง"
- OR["ไม่อาจ", "ไม่สามารถ", "ไม่ได้"] for "ได้มั้ย → ไม่ได้"
- "มีสิทธิ" for "มีสิทธิมั้ย → มี"

Review existing TCs for this pattern when adding new ones.

---
*Added via Oracle Learn*
