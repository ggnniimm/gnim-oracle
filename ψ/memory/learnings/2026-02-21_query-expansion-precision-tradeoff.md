# Lesson: Query Expansion ทำลาย Precision สำหรับ Specific Legal Queries

**Date**: 2026-02-21
**Source**: Thai legal RAG — Option C live test

---

## Pattern

Query expansion (expand=True) สร้าง queries broad กว่า ทำให้ intro chunks ของกฎหมายหลัก (พ.ร.บ./ระเบียบ) ได้ score สูงและขึ้นมาใน top 5 แทนที่ specific chunks ที่ query ต้องการจริงๆ

## Symptoms

- Query: "ข้อ 11 กฎกระทรวงผู้ประกอบการ"
- With expand=True → top 5 = พ.ร.บ. mาตรา 1, ระเบียบ ข้อ 1, ข้อหารือ กวจ.
- With expand=False → top 5 = กฎกระทรวงฯ ข้อ 11-12 (ถูกต้อง)

## Fix

Detect "specific" queries และ disable expansion:
- มีเลขข้อ/มาตรา: "ข้อ 11", "มาตรา 60"
- มีชื่อกฎหมายเฉพาะ: "กฎกระทรวง", "ฉบับที่ X"
- สั้น + เฉพาะเจาะจง

## Also

Python 3.10+: `asyncio.get_event_loop()` ไม่สร้าง loop ใหม่ใน main thread
→ Fix:
```python
try:
    loop = asyncio.get_running_loop()
    import nest_asyncio; nest_asyncio.apply()
    return loop.run_until_complete(...)
except RuntimeError:
    return asyncio.run(...)
```

## API Key Safety

ไม่ hardcode API key ใน bash command ที่โชว์ใน conversation
→ ใช้ `source .env && GEMINI_API_KEY="$GEMINI_API_KEY" python3 ...` เสมอ
→ Google auto-detects leaked keys และ block ทันที
