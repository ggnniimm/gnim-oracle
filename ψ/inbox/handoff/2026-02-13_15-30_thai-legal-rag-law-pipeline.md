# Handoff: Thai Legal RAG — Law Pipeline

**Date**: 2026-02-13 15:30 GMT+7
**Context**: ~96%

## What We Did

### date cross-check from filename (commit 9680c7d)
- เพิ่ม `_fix_date_from_filename()` ใน `ocr.py` — parse DDMMYY จาก filename segment 3
- แก้ไข 20/24 MD files ที่ date_be/date ผิด
- Patch FAISS metadata.pkl: 573/637 chunks อัพเดต date field

### Law RAG Pipeline (commits 8db57dc, 16cb2f3)
- **`law_extractor.py`**: PyMuPDF extraction + Gemini fallback, parse ภาค/หมวด/มาตรา hierarchy
- **`chunker_law.py`**: group มาตรา/ข้อ ใน หมวด เดียวกัน ≤800 chars, context header
- **`batch_index_law.py`**: CLI — Drive "Law" folder → extract → chunk → dedup → index
- **config.py**: เพิ่ม `DRIVE_FOLDER_LAW` env var
- **faiss_store.py**: fix batch limit 100 (was sending all chunks in 1 call)
- Index: พรบ (126 sections → 103 chunks) + ระเบียบ (230 sections → 179 chunks)
- FAISS: 637 → **919 vectors**

### Query test สำเร็จ
- "มาตรา 60 บอกว่าอะไร" → ดึง law text ตรงๆ score 0.787 + ข้อหารือ + คำตอบครบถ้วน

## Pending

- [ ] เพิ่มกฎกระทรวง — upload Drive "Law" แล้ว `python pipeline/batch_index_law.py`
- [ ] LightRAG re-index รวมกฎหมาย — ตอนนี้ law chunks ยังไม่อยู่ใน LightRAG graph
- [ ] Streamlit UI — interactive query interface (plan เดิมมีอยู่)
- [ ] ทดสอบ query ที่ใช้ทั้ง ข้อหารือ + law ร่วมกัน (cross-document)
- [ ] `clear_cache(file_id)` helper ใน ocr.py

## Next Session

- [ ] Upload กฎกระทรวงทั้งหมดไป Drive "Law" folder แล้วรัน batch_index_law.py
- [ ] LightRAG: index law + ข้อหารือ รวมกัน (ต้องล้าง LightRAG store เดิมแล้ว re-index ทั้งหมด หรือ add เฉพาะ law)
- [ ] ตรวจสอบ LightRAG graph: entity "มาตรา 60" เชื่อม ข้อหารือ ↔ law text หรือยัง
- [ ] Streamlit UI สำหรับ query

## Key Files

- `ψ/lab/thai-legal-rag/src/ingestion/law_extractor.py` — ใหม่
- `ψ/lab/thai-legal-rag/src/ingestion/chunker_law.py` — ใหม่
- `ψ/lab/thai-legal-rag/pipeline/batch_index_law.py` — ใหม่
- `ψ/lab/thai-legal-rag/src/indexing/faiss_store.py` — batch fix
- `ψ/lab/thai-legal-rag/src/ingestion/ocr.py` — date + doc_number cross-check
- `ψ/lab/thai-legal-rag/src/config.py` — DRIVE_FOLDER_LAW

## State

- FAISS: 919 vectors (637 ข้อหารือ + 282 law) — พรบ + ระเบียบ indexed
- LightRAG: 87MB graph — ข้อหารือ 24 files เท่านั้น (law ยังไม่ได้ index)
- MD backup: 24 ข้อหารือ + 2 law files
- Drive "Law" folder: พรบ + ระเบียบ (กฎกระทรวง ยังไม่ได้ upload)
- `.env`: DRIVE_FOLDER_LAW=1npincZiUuBkTi68y79ZOJWOOLoxvX2h3
