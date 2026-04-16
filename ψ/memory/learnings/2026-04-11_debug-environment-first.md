---
date: 2026-04-11
tags: [debugging, workflow, environment, production]
---

# Always Confirm Environment Before Debugging

## Pattern

เมื่อ user รายงาน bug ใน UI/app สิ่งแรกที่ต้องถามคือ **"ทดสอบที่ไหน?"** ก่อนเริ่มแก้อะไรทั้งนั้น

## What Happened

Session นี้ใช้เวลา 4 ชั่วโมงแก้ bug บน localhost ทั้งที่ user ใช้ mwaprocure.gnim.cloud มาตลอด ทำให้งานทั้งหมด (patch Qdrant local, patch BM25 local, restart local Streamlit) ไม่มีผลกับปัญหาจริงเลย

## Root Cause ของ Bug จริง

Key mismatch ใน `streamlit_app.py`:
- `_build_source_map` เก็บ URL ใน key `"url"`
- new answer rendering ดึงด้วย `s.get("drive_id", "")` ← ไม่มีอยู่จริง
- ผลคือ link ว่างเสมอ ทั้งๆ ที่ data ถูกต้อง

## Rules

1. **ถาม environment ก่อนเสมอ**: localhost? mwaprocure? server ไหน?
2. **อ่านโค้ดก่อน assume**: grep หา key ที่ใช้ก่อน assume ว่าเป็นปัญหา data
3. **Verify เองก่อนบอก user**: run pipeline จริง ดูผลจริง ก่อนรายงาน
4. **แก้ปัญหาที่ถูกขอ**: ไม่เพิ่ม feature ระหว่าง bug fix session

## Docker Deploy Rules

- `docker compose restart` = ใช้ image เดิม ไม่ได้ code ใหม่
- `docker compose build app && docker compose up -d app` = ได้ code ใหม่
- volume mount เฉพาะ `./data` ไม่ใช่ `./app` หรือ `./src`
