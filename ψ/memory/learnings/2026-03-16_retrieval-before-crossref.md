---
name: Check retrieval before adding cross-refs
description: Always verify which documents are actually retrieved for a failing query before editing any document
type: feedback
---

เมื่อ TC fail เพราะ must_contain ไม่เจอ keyword — ตรวจสอบว่า doc ที่ถูก retrieve มาจริงๆ คืออะไรก่อน แล้วค่อย add cross-ref ใส่ doc นั้น

**Why:** Session 2026-03-16 — เพิ่ม ป.พ.พ. ใน สรุปข้อวินิจฉัย ของ อ.100/2564 แต่ doc นั้นไม่ถูก retrieve เลย query ดึง อ.73/2565 ขึ้นมาแทน ต้องแก้ซ้ำสองครั้ง

**How to apply:** ก่อน edit doc ใดก็ตาม ให้รัน `python3 eval/run_eval.py --id TC-XXX --verbose` ดู Sources ที่ขึ้นมาก่อน แล้วค่อย add cross-ref ใส่ top-retrieved doc นั้น ไม่ใช่ doc ที่เราคิดว่า "น่าจะ" retrieved
