# MD Frontmatter คือ Source of Truth สำหรับ Drive file_id

**Date**: 2026-04-14
**Context**: Production Qdrant patch — broken Drive links in web app

## บทเรียน

เมื่อมีหลาย source สำหรับข้อมูลเดียวกัน (Drive file_id ปรากฏใน xlsx, MD frontmatter, และ Qdrant payload) ต้องถามก่อนว่าอันไหนคือ source of truth จริง

**สำหรับ thai-legal-rag:**
- **MD frontmatter (`file_id:`)** — source of truth ✅ (verified จาก Drive audit 2026-04-08)
- **`document_list.xlsx` col 8** — inventory tracker, มักจะ stale ❌ (1,268 IDs ผิดจาก 1,383 ไฟล์)
- **Qdrant payload `file_id`** — derived, ต้อง patch จาก MD เสมอ

## กฎ

ก่อน patch Qdrant file_ids ด้วย script ใดๆ ให้ cross-check:
```python
# Quick sanity check: sample 10 files
for md, xlsx_id in zip(sample_mds, sample_xlsx_ids):
    md_id = get_frontmatter_id(md)
    assert md_id == xlsx_id, f"MISMATCH: {md.name}"
```

ถ้า mismatch → ใช้ MD เป็น source of truth เสมอ

## Script ที่ถูกต้อง

ใช้ `/tmp/patch_qdrant_from_md.py` (สร้าง 2026-04-14) ซึ่งอ่าน MD frontmatter โดยตรง ไม่ใช้ xlsx

```bash
python3 -c "..."  # build md_file_id_mapping.json จาก MD files
QDRANT_URL=http://172.22.0.2:6333 python3 patch_qdrant_from_md.py
```

## Snapshot ก่อน patch

```bash
curl -X POST http://{qdrant_ip}:6333/collections/thai_legal_rag/snapshots
```
