# Lesson: --cleanup และ --resplit กับ Gemini — danger zone

**Date**: 2026-02-20
**Project**: thai-legal-rag

## ปัญหา

`--cleanup` และ `--resplit` ใน `pipeline/regenerate_sections.py` รัน Gemini กับ **ทุก section** (355 sections) ไม่ใช่แค่ section ที่เปลี่ยน

- ถ้า Gemini key ผิด → fallback blank-line split → diffs พุ่ง (88 → 159 ในวันนี้)
- Env var ชื่อ `GEMINI_API_KEY_1_ggnngm` ต้อง pass เป็น `GEMINI_API_KEY=...` ตอนรัน

## วิธีรัน (ถูกต้อง)

```bash
cd ψ/lab/thai-legal-rag
THAI_RAG_DATA_DIR=$(pwd)/data \
  GEMINI_API_KEY=$(grep "GEMINI_API_KEY_1" /Users/mingsaksaengwilaipon/gnim-oracle/.env | cut -d= -f2) \
  python3 pipeline/regenerate_sections.py --cleanup
```

หรือใช้ key โดยตรง: `GEMINI_API_KEY=REDACTED-leaked-public-repo-rotated-2026-05-08`
<!-- Original key was leaked in public repo since 2026-02-21 — rotated and redacted 2026-05-08 -->


## ตรวจสอบก่อนรัน

```bash
# ตรวจว่า key ถูกต้องก่อน
python3 -c "import google.generativeai as genai; genai.configure(api_key='KEY'); print('ok')"
```

## ถ้า diffs พุ่งขึ้นหลัง --cleanup

รัน `--resplit` ด้วย key ที่ถูกต้องเพื่อ recover:
```bash
GEMINI_API_KEY=... python3 pipeline/regenerate_sections.py --resplit
```
