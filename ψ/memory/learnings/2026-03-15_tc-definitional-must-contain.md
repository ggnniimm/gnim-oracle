---
name: TC definitional questions — must_contain should use concept words
description: For "คืออะไร" type TCs, use generic semantic words not specific phrases
type: feedback
---

TC ประเภท "คืออะไร" (definitional) มี LLM variance สูง เพราะ LLM เลือกคำตอบได้หลากหลาย

**Rule:** must_contain สำหรับ definitional TC ให้ใช้ concept words ที่ semantic สูงและมักปรากฏในทุกคำตอบที่ดี — เช่น "ความระมัดระวัง", "ชดใช้", "ละเมิด" ไม่ใช่ specific legal phrase อย่าง "จงใจ" หรือ "มาตรา 8" ซึ่ง LLM อาจเลือกไม่พูดถึง

**Why:** TC-065 "ประมาทเลินเล่อย่างร้ายแรง คืออะไร" ต้องรัน 3 รอบ — must_contain "จงใจ" fail, "ชดใช้" fail ครั้งที่สอง, ถึงผ่านครั้งที่สาม สะท้อน variance สูงของ definitional queries

**How to apply:** ก่อน set must_contain ให้ถามตัวเองว่า "ทุกคำตอบที่ดีจะต้องมีคำนี้เสมอมั๊ย?" ถ้าไม่แน่ใจ ให้เลือกคำที่ broad กว่า หรือรัน query 2-3 รอบก่อนแล้วดูว่าคำไหน stable
