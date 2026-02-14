# Thai Legal RAG — Design Lessons

**Date**: 2026-02-14
**Source**: Session retrospective

---

## 1. PDF Format กำหนด Parser ไม่แพ้ Content

ราชกิจจานุเบกษา format เลข มาตรา 1-9 คนละบรรทัดกับ "มาตรา" (`มาตรา\n๑`) ขณะที่ มาตรา 10+ อยู่บรรทัดเดียวกัน regex ที่ไม่รู้เรื่องนี้จะ miss sections ไปเงียบๆ

**Fix pattern**: normalize before parse — `_normalize_section_headers()` จับทั้งสองรูปแบบ

---

## 2. Vision AI vs Text Parser Tradeoff สำหรับ Thai Law

| | PyMuPDF | LandingAI |
|---|---|---|
| Section coverage | ✅ สูงกว่า (132 vs 115) | ❌ ต่ำกว่า |
| รูปภาพ/ตรา | ❌ | ✅ describe ได้ |
| Bounding box | ❌ | ✅ |
| Scan PDF | ❌ | ✅ |
| Speed | เร็ว | ช้า (2+ นาที) |

→ สำหรับ structured Thai law: **PyMuPDF + Gemini fallback** ยังดีกว่า LandingAI
→ LandingAI มีคุณค่าถ้าต้องการ bounding box หรือเจอ scan-only PDF

---

## 3. Metadata Schema Design สำหรับ Multi-Type RAG

**Core fields** (ทุก doc type):
- `doc_type`, `date`, `date_be`, `topic`, `laws_referenced`, `status`

**Bridge field**: `laws_referenced` — ทำให้ query "มาตรา 56 มีหนังสือหารืออะไรบ้าง" เป็นไปได้

**Type-specific**: พ.ร.บ. → `law_name`, `law_year_be` | หนังสือหารือ → `issued_by`, `doc_number`, `quality`

---

## 4. Context Header ใน Chunk ช่วย Embedding

แทนที่จะ embed "มาตรา ๕๖ ..." โดดๆ ควรเป็น:
```
[พ.ร.บ.จัดซื้อจัดจ้างฯ 2560 | หมวด ๕]
มาตรา ๕๖ ...
```
Embedding จะมี signal ของ law + chapter ทำให้ retrieval แม่นขึ้น

---

## 5. ตาม Git ไม่พอ — ต้องตาม Conversation ด้วย

Schema อาจมาจาก conversation ก่อน commit ไม่ใช่ commit เอง เวลา trace origin ของ design decision ต้องระวัง under-claim contribution ของ Gnim
