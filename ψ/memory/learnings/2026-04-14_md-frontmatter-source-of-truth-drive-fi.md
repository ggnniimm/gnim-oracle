---
title: MD frontmatter คือ source of truth สำหรับ Drive file_id ใน thai-legal-rag
tags: [qdrant, drive-file-id, source-of-truth, patch, production, thai-legal-rag]
created: 2026-04-14
source: rrr: gnim-oracle-qdrant
---

# MD frontmatter คือ source of truth สำหรับ Drive file_id ใน thai-legal-rag

MD frontmatter คือ source of truth สำหรับ Drive file_id ใน thai-legal-rag

เมื่อมีหลาย source สำหรับ file_id เดียวกัน:
- MD frontmatter (`file_id:`) = verified, ถูกต้อง ✅
- document_list.xlsx = stale, อาจผิด ❌ (พบ 1,268 mismatches จาก 1,383 ไฟล์)
- Qdrant payload = derived, ต้อง patch จาก MD เสมอ

ก่อน mass patch production Qdrant ให้ cross-check sources ก่อนเสมอ และ snapshot ก่อน patch:
`POST /collections/thai_legal_rag/snapshots`

Script ที่ถูกต้อง: patch_qdrant_from_md.py (อ่าน MD frontmatter โดยตรง ไม่ใช้ xlsx)

---
*Added via Oracle Learn*
