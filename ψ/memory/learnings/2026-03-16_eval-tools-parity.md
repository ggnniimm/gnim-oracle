---
name: Eval tools must stay in sync (run_eval.py ↔ export_answers_csv.py)
description: Both eval tools implement must_contain checking — they must support the same features
type: feedback
---

`run_eval.py` และ `export_answers_csv.py` ต่างก็ implement `must_contain` checking แยกกัน — ต้อง sync feature ให้ตรงกันเสมอ

**Why:** Session 2026-03-16 — export_answers_csv.py รองรับ array-of-arrays (OR logic) มาก่อนแล้ว แต่ run_eval.py ไม่รองรับ ทำให้ TC ที่ใช้ `["ป.พ.พ.", "ประมวลกฎหมายแพ่ง"]` crash เฉพาะตอนรัน run_eval.py

**How to apply:** เมื่อ add feature ใหม่ใน must_contain logic ของ tool ใด tool หนึ่ง ให้ update อีก tool ด้วยทันที ในอนาคตควร extract `_check_case()` เป็น shared utility ใน `eval/utils.py`
