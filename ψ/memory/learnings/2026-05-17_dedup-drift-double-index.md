---
name: dedup-drift-double-index
description: dedup.db อาจนับ chunk น้อยกว่า Qdrant จริงเนื่องจาก double-index เก่า — ไม่กระทบ eval แต่ทำให้ตัวเลขสับสน
metadata:
  type: project
---

## Fact

Local Qdrant อาจมี chunk มากกว่าที่ dedup.db รู้จัก เนื่องจาก double-index ในอดีต (ก่อน dedup track ครบ) พบ 2,181 extra chunks ใน 161 files หลายไฟล์มี Qdrant = 2x dedup rows พอดี

**Why:** indexer เก่าไม่มี dedup หรือ dedup ถูก reset แต่ Qdrant ไม่ถูก reset — chunks ที่ index ซ้ำยังอยู่ใน Qdrant แต่ dedup ไม่รู้จัก

**How to apply:**
- ถ้า dedup rows < Qdrant points ไม่ต้องตกใจ — MMR/rerank handle duplicate ได้
- ถ้าอยาก clean ต้อง rebuild Qdrant ทั้งหมด (ลบ collection + ล้าง dedup + reindex ใหม่ ~4-6h)
- ตัวเลข Qdrant points คือ source of truth สำหรับ "จำนวน chunk จริง" ไม่ใช่ dedup rows
- Verify ด้วย `curl http://localhost:6333/collections/thai_legal_rag` เสมอ

Related: [[verify-before-act]]
