---
name: Legal RAG — doc_type priority ใน reranker
description: คำพิพากษาควรได้ score boost เหนือ กวจ./คำวินิจฉัย ใน legal RAG
type: feedback
---

ใน legal RAG ลำดับ authority ของ source ต้องสะท้อนใน reranker score ด้วย ไม่ใช่แค่ semantic similarity

**Rule:** เพิ่ม `_CATEGORY_BOOST` ใน reranker เพื่อให้ category "ศาลปกครอง" ได้ boost >1.0 เหนือ กวจ./กรมบัญชีกลาง เสมอ ลำดับที่ถูกต้องสำหรับ legal reasoning:
1. คำพิพากษา (ศาลปกครอง) — หลักกฎหมายที่ผูกพัน
2. คำวินิจฉัยอัยการสูงสุด — ตีความกฎหมาย
3. กวจ./กรมบัญชีกลาง — แนวปฏิบัติ

**Why:** Ming ตั้งคำถาม session 2026-03-15 ว่า "ควรหาแนวทางปฏิบัติที่ดีจากคำพิพากษาก่อน ค่อยไปดู กวจ. ไม่ใช่หรอ?" — ระบบเดิมดึง กวจ. ขึ้นก่อนทุกครั้งเพราะ query เชิงปฏิบัติ match กับ กวจ. ดีกว่า ทำให้คำตอบเน้น procedure แทนที่จะเน้น legal principle

**How to apply:** `_CATEGORY_BOOST = {"ศาลปกครอง": 1.15, "สำนักงานอัยการสูงสุด": 1.05}` ใน `src/retrieval/reranker.py` apply หลัง normalize score ก่อน recency boost ถ้าต้องการให้ case law ขึ้น top ต้องเพิ่มเป็น 1.3+ แต่ต้องทดสอบ regression ก่อน
