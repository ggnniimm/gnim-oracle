# Handoff: Citation Accuracy & MMR Investigation

**Date**: 2026-04-17 21:15
**Session**: 485fc355
📡 Session: 485fc355 | gnim-oracle-qdrant | ~3h

## Context
**Oracle**: Gnim | **Human**: Ming
**Branch**: fix/stale-cookie-and-rag-improvements

---

## What We Did

### กวจ_22315 ranking improvements
- เพิ่ม bullet เนื้องาน ให้เป็น bullet แรกใน สรุปข้อวินิจฉัย (เดิมเป็น bullet สุดท้าย)
- เพิ่ม BM25 keywords ใน บทสรุปสำหรับสืบค้น: `แก้ไขสัญญาหลังตรวจรับงานงวดสุดท้าย แก้ไขสัญญาหลังตรวจรับพัสดุงวดสุดท้าย รายละเอียดของเนื้องาน ไม่เกี่ยวกับเนื้องาน มาตรา ๙๗ ข้อ ๑๖๕`
- เพิ่ม "หลัง" ใน สรุปข้อวินิจฉัย bullet แรก เพื่อ boost vector similarity กับ query ที่ใช้คำ "หลัง"
- ผล BM25: กวจ_22315 ขึ้นมาที่ [3][4] ใน BM25 pool แต่ vector ยังต่ำ [27] → combined ไม่ติด top 15

### Generator rule 15
- เพิ่ม rule 15: "ห้าม cite [N] เอกสารที่ไม่มีข้อความนั้นอยู่จริง"
- Deploy แล้วบน server

### Production deploy
- กวจ_22315: re-index บน server แล้ว (62 chunks)
- rule 15: deploy แล้ว
- ไม่ต้องทำอะไรเพิ่มในส่วน deploy

### Cross-ref audit คำวินิจฉัยที่_๑๔๒_๒๕๖๔
- ตรวจสอบ PDF จริงด้วย Gemini OCR
- พบว่า MD file มี cross-ref ที่เราเพิ่มเองใน ข้อวินิจฉัย body และ สรุปข้อวินิจฉัย
- เอา cross-ref ออกแล้ว (ข้อมูลสะอาดขึ้น), TC-008 ยัง PASS
- คำวินิจฉัย 142 ยัง rank [2] เพราะ body อ้าง กวจ_22315 ในเนื้อหาจริง

### Root cause ของ citation problem
- กวจ_22315 ถูก MMR diversity penalty ดัน score ลง เพราะ content คล้ายกับ docs อื่นที่ rank สูงกว่า
- BM25 ดี [3][4] แต่ vector [27] → combined RRF ไม่ติด top 15
- ตราบที่กวจ_22315 ไม่ใน top 15 — LLM จะ cite เอกสารอื่นสำหรับ rule เนื้องาน (hallucination)
- คำตอบถูก แต่ citation ผิด

### Eval
- Local: **76/79 PASS** (TC-027, TC-037, TC-071 fail — เหมือนก่อน ไม่ regression)

---

## Pending

- [ ] แก้ citation problem จริงๆ: เลือกวิธี (MMR_LAMBDA หรือ cross-ref ใน 51385/27093)
- [ ] Deploy คำวินิจฉัย 142 cross-ref removal ขึ้น server
- [ ] Deploy กวจ_22315 "หลัง" keyword change ขึ้น server
- [ ] Run full eval บน server (Gemini 503 บ่อย ควรรันตอนเช้า/กลางคืน)
- [ ] TC-027, TC-037 ยังแก้ไม่ได้ (ไม่ใช่ regression จาก session นี้)

---

## Next Session

- [ ] **ตัดสินใจ**: MMR_LAMBDA 0.7→0.8 vs cross-ref text ใน กวจ_51385 [1]
  - ถ้า MMR_LAMBDA: แก้ config.py แล้ว run full eval ดู regression
  - ถ้า cross-ref: เพิ่ม rule เนื้องาน ใน กวจ_51385 สรุปข้อวินิจฉัย แล้ว re-index
- [ ] Deploy all local changes ขึ้น server (คำวินิจฉัย 142 + กวจ_22315)
- [ ] Run full eval ตอนเช้า (off-peak Gemini)

---

## Key Files

- `ψ/lab/thai-legal-rag/data/md_backup/กวจ_0405.4_22315_170564_แก้ไขสัญญาเกี่ยวกับเนื้องานต้องก่อนตรวจรับงานงวดสุดท้าย หากไม่เกี่ยวกับเนื้องานแก้หลังได้.md` — updated (BM25 boost + "หลัง" + bullet reorder)
- `ψ/lab/thai-legal-rag/data/md_backup/คำวินิจฉัยที่_๑๔๒_๒๕๖๔.md` — cross-ref removed (local only, ยังไม่ deploy)
- `ψ/lab/thai-legal-rag/src/generation/generator.py` — rule 15 deployed
- `ψ/lab/thai-legal-rag/src/config.py` — MMR_LAMBDA=0.7 (ยังไม่แก้)

## New Idea (ยังไม่ implement)

**Query-type-based response length** — ให้ LLM พิจารณาก่อนตอบว่าเป็น query แบบไหน:
- yes/no ("ทำได้มั๊ย") → ตอบสั้น verdict ก่อน แล้วอธิบาย
- enumerate ("มีหน้าที่อะไรบ้าง") → ตอบครอบคลุม bullet
- explain ("เพราะอะไร") → อธิบายพอเข้าใจ

วิธีทำ: เพิ่ม rule ใน generator system prompt (ง่าย แต่ rule density สูงแล้ว) หรือ pre-classify query type แล้วส่ง instruction ต่างกัน (ซับซ้อนกว่า แต่แม่นกว่า)

---

## Key Insight

**กวจ_22315 vector score ต่ำเพราะ doc ครอบคลุมหลายเรื่อง (6 questions) ทำให้ embedding diluted**
**MMR diversity penalty ดันออกจาก top 15 แม้ BM25 จะดี [3][4]**
**คำวินิจฉัย 142 rank [2] ด้วยเนื้อหาจริง ไม่ใช่ cross-ref ที่เราเพิ่ม**
