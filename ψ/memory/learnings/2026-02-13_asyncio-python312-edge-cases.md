# Lesson: asyncio.coroutine + Edge Case Testing Patterns

**Date**: 2026-02-13
**Source**: Thai Legal RAG edge case testing session

---

## 1. asyncio.coroutine ถูก remove ใน Python 3.11+

`asyncio.coroutine` decorator ถูก deprecate ตั้งแต่ Python 3.8 และถูก remove จริงใน Python 3.11 (ไม่ใช่ 3.12 อย่างที่คิด)

**ผิด (Python 3.11+):**
```python
else asyncio.coroutine(lambda: [])()
```

**ถูก:**
```python
async def _empty_coroutine() -> list:
    return []

# ...
else _empty_coroutine()
```

---

## 2. Chunk structure จาก reranker เป็น flat dict

Chunks ที่ผ่าน `rerank()` จาก `src/retrieval/reranker.py` เป็น flat dict ไม่มี nested `metadata` key:

```python
# ผิด
chunk['metadata']['source_name']

# ถูก
chunk.get('source_name', '')
```

---

## 3. Semantic search ข้ามภาษา (EN → TH)

Gemini embedding (`gemini-embedding-001`) สามารถ match English query กับ Thai documents ได้ดี เพราะ embedding multiligual — ไม่ต้องแปล query ก่อน

---

## 4. System Prompt Persona = Scope Guard

การให้ persona เฉพาะ ("นิติกรชำนาญการพิเศษ ด้านกฎหมายจัดซื้อจัดจ้าง") ช่วยให้ LLM:
- ปฏิเสธ irrelevant queries อย่างสุภาพ
- Redirect ไปแหล่งข้อมูลที่ถูกต้อง
- ขอ clarification เมื่อ query คลุมเครือ

ดีกว่าการเขียน explicit "if query is unrelated, say X" ใน prompt

---

## 5. grep API ก่อน test

เมื่อไม่แน่ใจ API ของ module ที่เขียนเอง ควร grep ก่อน:
```bash
grep "^def \|^class " src/generation/generator.py
```
ดีกว่าลองแล้วแก้ ImportError ทีละรอบ
