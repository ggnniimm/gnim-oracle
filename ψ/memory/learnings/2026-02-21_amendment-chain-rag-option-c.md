# Lesson: Amendment-Aware RAG via Prompt Engineering (Option C)

**Date**: 2026-02-21
**Source**: Thai legal RAG — กฎกระทรวง batch OCR session

---

## Pattern

เมื่อ FAISS index มีหลายฉบับของกฎหมายเดียวกัน (BASE + amendments) LLM ต้องรู้ว่าฉบับไหนล่าสุดเพื่อตอบได้ถูก

## Solution (Option C — Prompt Engineering)

**ขั้นตอน:**
1. Ensure `law_year_be` อยู่ใน FAISS metadata ทุก chunk (ตรวจสอบตอน index)
2. Surface `law_year_be` ใน context string ที่ส่งให้ LLM:
   ```python
   year_str = f" [พ.ศ. {law_year_be}]" if law_year_be else ""
   parts.append(f"[{i}] **{source}**{year_str} ({category})\n{text}")
   ```
3. เพิ่ม rule ใน system prompt:
   ```
   6. กฎหมายบางฉบับมีหลายเวอร์ชัน — หากมีหลายฉบับในปี พ.ศ. ต่างกัน ให้ยึดฉบับ พ.ศ. สูงสุด (ล่าสุด) เป็นหลัก และแจ้งผู้ถามว่าฉบับเก่าถูกแก้ไข/ยกเลิกแล้ว
   ```

## Trade-offs

| Option | Speed | Quality | Re-index? |
|--------|-------|---------|-----------|
| A: Consolidation | ช้า | ดีมาก | ใช่ |
| B: Status metadata + filter | กลาง | ดี | ใช่ |
| C: Prompt engineering | เร็วมาก | พอใช้ | ไม่ |

Option C เป็น MVP — ใช้ metadata ที่มีอยู่แล้ว ไม่ต้อง re-pipeline
Ceiling: FAISS ยังดึง old-version chunks ขึ้นมา กิน context window

## Related Fix

กฎกระทรวง signature: `ให้ไว้ ณ วันที่` (ต่างจาก พ.ร.บ. ที่ใช้ `ประกาศ ณ วัน`)
→ `_SIGNATURE_BLOCK_RE` ต้องรองรับทั้งสองรูปแบบ
