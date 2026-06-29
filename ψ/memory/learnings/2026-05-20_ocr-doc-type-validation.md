---
name: ocr-doc-type-validation
description: หลัง OCR ต้องตรวจ doc_type vs filename + section headers ก่อน index — กวจ 8938 classify ผิดเป็น หนังสือเวียน
metadata:
  type: feedback
---

ถ้าชื่อไฟล์มีคำว่า "ข้อหารือ" แต่ doc_type ไม่ใช่ "ข้อหารือ" หรือไม่มี `## สรุปข้อวินิจฉัย` ในเนื้อหา → re-OCR ด้วย `force=True` ทันที

**Why:** กวจ 8938 ถูก Gemini classify เป็น "หนังสือเวียน" เพราะเนื้อหา hybrid (คำถาม 8 ข้อ + คำตอบ กวจ) ทำให้ section headers ผิด (หลักการและที่มา/แนวปฏิบัติ) ขาด สรุปข้อวินิจฉัย ซึ่งสำคัญมากสำหรับ RAG retrieval รู้จาก Ming สังเกตด้วยตา — ไม่มี automated check

**How to apply:** หลัง OCR ทุกไฟล์ ให้ check 2 เงื่อนไข:
1. filename มี "ข้อหารือ" แต่ doc_type ≠ "ข้อหารือ" → flag
2. `## สรุปข้อวินิจฉัย` ไม่มีใน text → flag

ถ้า flag → re-OCR ด้วย force=True ก่อน index เสมอ Re-OCR รอบ 2 มักถูกต้องเพราะไม่มี cached context ผิดมา confuse
