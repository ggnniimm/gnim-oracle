---
name: must_contain criteria must match question type
description: When writing must_contain, check if the criterion fits the question type (definition/consequence/procedure) — not just whether the source doc contains the word
type: feedback
---

เมื่อเขียน must_contain สำหรับ TC ใหม่ ต้องถามว่า "คำตอบที่ถูกต้องสำหรับคำถามนี้โดยตรง จะมีคำนี้ไหม?" ไม่ใช่ "เอกสารอ้างอิงมีคำนี้ไหม?"

**Rule:** จับคู่ must_contain กับ question type:
- คำถาม "คืออะไร" → ตรวจ keyword เชิงนิยาม (definition terms)
- คำถาม "ผลเป็นอย่างไร" → ตรวจ keyword เชิงผลลัพธ์ (consequence terms เช่น ชดใช้, รับผิด)
- คำถาม "ทำอย่างไร" → ตรวจ keyword เชิงขั้นตอน (procedural terms)

**Why:** TC-065 "ประมาทเลินเล่ออย่างร้ายแรง คืออะไร" — must_contain มี "ชดใช้" (consequence) แต่คำถามถามนิยาม LLM ตอบนิยามถูกต้อง แต่ test fail เพราะ criterion ผิด type ต้องแก้เป็น OR: `["ชดใช้", "รับผิด"]`

**How to apply:** ก่อน add must_contain ทุกครั้ง ให้ถามตัวเองว่า "ถ้าตอบคำถามนี้อย่างถูกต้องและตรงประเด็น จะพูดถึงคำนี้ด้วยไหม?" ถ้าไม่แน่ใจ ใช้ OR เพื่อรองรับ variant ที่ legitimate
