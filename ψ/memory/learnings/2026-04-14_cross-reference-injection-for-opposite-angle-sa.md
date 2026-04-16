---
title: ## Cross-Reference Injection for Opposite-Angle Same-Topic Queries
tags: [cross-ref, retrieval, semantic-similarity, legal-rag, thai-legal-rag, opposite-angle]
created: 2026-04-14
source: 2026-04-09 learning
---

# ## Cross-Reference Injection for Opposite-Angle Same-Topic Queries

## Cross-Reference Injection for Opposite-Angle Same-Topic Queries

When a query semantically matches a document that covers the **opposite legal conclusion** on the same topic, cross-ref injection in that doc's สรุปข้อวินิจฉัย can redirect the LLM to the correct answer.

**Example**:
- Query: "ครบกำหนดตรงกับวันหยุด ส่งมอบวันทำการถัดไปได้ไหม" (answer: ได้)
- Rank #1 retrieves: คำวินิจฉัย 167/2561 about "ขยายระยะเวลากรณีวันหยุด" (answer: ไม่ได้)
- Same topic (วันหยุด + สัญญาก่อสร้าง) but opposite angle
- Fix: cross-ref in rank #1's สรุปข้อวินิจฉัย pointing to ป.พ.พ. ม.193/8 from กวจ 51349

**Why It Works**: The LLM reads all retrieved chunks. When chunk A says "วันหยุดไม่ใช่เหตุขยาย" and chunk B (cross-ref) says "แต่ส่งมอบวันทำการถัดไปได้ตาม ม.193/8", the LLM can distinguish the two principles and answer correctly.

**When to Use**:
- Query matches topic X but doc covers conclusion Y (opposite)
- The correct doc exists but ranks too low for retrieval
- The two conclusions are legally distinct (not contradictory — they address different sub-questions)

---
*Added via Oracle Learn*
