---
name: RAG negative annotation — tell the document what NOT to be cited for
description: When LLM keeps misciting a document for wrong claim, add explicit "อย่าอ้างฉบับนี้เป็นหลักฐานว่า X" to บทสรุปสำหรับสืบค้น
type: feedback
date: 2026-04-18
---

When a document is repeatedly miscited for a claim it doesn't support, two fixes are needed — not one.

**Why:** Category confusion (wrong bucket) ≠ direction confusion (right topic, wrong direction). If you only clarify what the document IS about, the LLM may still associate it with the wrong claim through semantic overlap in the general rule passages.

**How to apply:**
1. State what the document IS: "กรณีนี้เกี่ยวกับ X ซึ่งยังมิได้ตรวจรับงานงวดสุดท้าย"
2. State what it is NOT: "อย่าอ้างหนังสือฉบับนี้เป็นหลักฐานว่า Y ทำได้"

Example fix for 51385 (miscited as supporting "แก้ไขหลังตรวจรับได้"):
```
หนังสือฉบับนี้เกี่ยวกับการแก้ไขสัญญาที่เกี่ยวข้องกับรายละเอียดของเนื้องาน
ไม่ใช่กรณี "ไม่เกี่ยวกับรายละเอียดของเนื้องาน" ที่อาจแก้ไขหลังตรวจรับได้
อย่าอ้างหนังสือฉบับนี้เป็นหลักฐานว่าแก้ไขสัญญาหลังตรวจรับงานงวดสุดท้ายได้
```
