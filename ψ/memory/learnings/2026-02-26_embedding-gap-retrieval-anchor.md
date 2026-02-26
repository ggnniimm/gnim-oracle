# Embedding Gap & Retrieval Anchor

**Date**: 2026-02-26
**Project**: thai-legal-rag
**Context**: หนังสือ กวจ. 38381 ไม่ติด top 15 สำหรับ query "คณะกรรมการตรวจรับพัสดุมีหน้าที่อะไรบ้าง"

---

## Embedding Gap คืออะไร

**ระยะห่างระหว่าง query vector กับ chunk vector ที่ควรจะ relevant แต่อยู่ไกลกันใน embedding space**

Embedding model แปลงข้อความเป็น vector ใน high-dimensional space ข้อความที่ "ความหมายใกล้กัน" อยู่ใกล้กันใน space ถ้า query กับ chunk อยู่ใน semantic cluster ต่างกัน cosine similarity จะต่ำ แม้มนุษย์อ่านแล้วเห็นว่า relevant

## สาเหตุของ Gap

**1. Training data imbalance**
Embedding model train จาก general text ไม่มี Thai legal domain ดีพอ ไม่รู้ว่า "หน้าที่" ใน context กฎหมายจัดซื้อครอบคลุมทั้ง "ตรวจรับ" AND "เสนอความเห็น"

**2. Corpus imbalance**
ใน 32,000 chunks มี "หน้าที่ตรวจรับพัสดุ" หลายร้อย chunks แต่ "หน้าที่เสนอความเห็น" ไม่กี่ chunks embedding space ถูก shape ให้ "คณะกรรมการตรวจรับ + หน้าที่" → ตรวจรับ

**3. Vocabulary dilution (tug of war)**
เมื่อ chunk มีคำหลายกลุ่ม embedding = weighted average ของทุกคำ กลุ่มที่มีคำมากกว่าดึงแรงกว่า

```
chunk 38381:
  "หน้าที่" words: มีหน้าที่, เสนอความเห็น          ← 2-3 คำ
  "สัญญา" words:  แก้ไขสัญญา, ขยายระยะเวลา,        ← 6-7 คำ
                  งดลดค่าปรับ, บอกเลิกสัญญา,
                  มาตรา ๙๗, ๑๐๒, ๑๐๓

→ vector ลงจุดใน "บริหารสัญญา" cluster
→ ห่างจาก query "มีหน้าที่อะไรบ้าง" ที่อยู่ใน "หน้าที่" cluster
```

สำคัญ: ไม่ใช่แค่ "บอกเลิกสัญญา" คำเดียวที่ดึง แต่ทั้ง 4 กรณีสัญญาดึงพร้อมกันไปทิศเดียวกัน

**4. Perspective gap**
Query มอง "หน้าที่" แบบกว้าง open-ended
Chunk เล่าจากมุม "บริหารสัญญา" — context framing ต่างกัน

## ประเภท Gap ที่พบบ่อยใน RAG

| ประเภท | ตัวอย่าง |
|--------|---------|
| **Vocabulary gap** | query: "ยกเลิก" / chunk: "บอกเลิก" |
| **Abstraction gap** | query abstract / chunk concrete |
| **Domain gap** | model ไม่รู้ legal domain |
| **Perspective gap** | query กว้าง / chunk เฉพาะมุม |
| **Vocabulary dilution** | chunk มีเนื้อหาผสมหลาย cluster |

## วิธีแก้

### Option 1: Retrieval Anchor (แก้ที่ data)
เพิ่ม chunk สั้นๆ ที่ใช้ vocabulary ตรงกับ query เป็น "bridge" ระหว่าง query vector กับ content จริง

```markdown
## บทสรุปสำหรับสืบค้น
คณะกรรมการตรวจรับพัสดุมีหน้าที่เสนอความเห็น (ไม่ใช่ผู้มีอำนาจสั่งการ) กรณีแก้ไขสัญญา ขยายระยะเวลา งดลดค่าปรับ บอกเลิกสัญญา
```

~100 chars, focused, crfcut ไม่ตัด → embedding dense ใน "หน้าที่" space

**เมื่อใช้**: เอกสารที่รู้แน่ว่ามี gap และ query pattern ชัดเจน

### Option 2: เพิ่ม RERANK_TOP_K
เปลี่ยนจาก 15 → 20 → LLM เห็น context เพิ่ม tradeoff: LLM cost สูงขึ้น + context noise

### Option 3: Cross-Encoder Reranker (แก้ที่ architecture)
แทนที่ bi-encoder similarity (query ↔ chunk แยกกัน) ด้วย model ที่อ่านทั้ง query + chunk พร้อมกัน แล้ว reasoning ว่า relevant ไหม

```
Bi-encoder:     embed(query) · embed(chunk) = score
Cross-encoder:  model(query [SEP] chunk) = score
```

Cross-encoder ไม่ขึ้นกับ embedding space ทำให้แก้ perspective gap ได้ แต่:
- ต้องการ Thai legal cross-encoder หรือ Gemini เป็น reranker
- latency สูงขึ้น (ต้อง forward pass ทุก pair)
- เหมาะกว่าเมื่อ scale ใหญ่และ gap เกิดบ่อย

### Option 4: Query Expansion
Generate variant queries เช่น "หน้าที่เสนอความเห็นด้านบริหารสัญญา" ก่อน retrieve
→ ดูไฟล์ `2026-02-21_query-expansion-precision-tradeoff.md`

## Invariant

**Short, focused chunk = dense embedding = better ranking**

chunk ที่มีคำน้อยแต่ล้วนตรง topic → embedding อยู่ใน cluster นั้นชัดเจน
chunk ที่ผสมหลาย topic → embedding เป็นค่าเฉลี่ย อยู่กลางๆ ไม่ชนะใคร

stale 75-char overlap chunk ("มีหน้าที่เสนอความเห็น กรณีหน่วยงานต้องพิจารณาเรื่อง") ที่เราลบทิ้งนั้น rank 9 ได้เพราะ accidentally เป็น perfect retrieval anchor — บทเรียน: ความสั้นและ focus มีคุณค่า ถ้า content ครบถ้วน

## Related

- `rag.md` — RAG overview, bi/cross-encoder section
- `2026-02-21_query-expansion-precision-tradeoff.md`
- `2026-02-25_bm25-normalization-routing.md`
