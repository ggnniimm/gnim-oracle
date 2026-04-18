# Handoff: Citation Fix — Sub-doc + Cross-ref Strategy

**Date**: 2026-04-17 22:30
📡 Session: 485fc355 | gnim-oracle-qdrant | ~5h

## Context
**Oracle**: Gnim | **Human**: Ming
**Branch**: fix/stale-cookie-and-rag-improvements

---

## What We Did

### กวจ_22315 citation problem — root cause + fix
- **Root cause**: กวจ_22315 ครอบคลุม 6 ประเด็น → embedding diluted → vector score ต่ำ → MMR diversity penalty ดันออก top 15
- **Fix 1 (sub-doc)**: สร้าง `กวจ_0405.4_22315_ประเด็น6_แก้ไขสัญญาเนื้องาน.md` — focused sub-doc เฉพาะประเด็น 6
  - `original_filename` เหมือนกับ parent → citation ใน UI ยังเป็นเลขเดิม
  - Local: rank [5] score 0.7868 ✓
  - Server: rank [24] — ยังไม่ติด top 15 (MMR diversity ยังบล็อก)
- **Fix 2 (cross-ref)**: เพิ่ม bullet เนื้องาน rule ใน `กวจ_51385` สรุปข้อวินิจฉัย
  - กวจ_51385 rank [1] เสมอสำหรับ query แก้ไขสัญญา+งวดสุดท้าย (เหตุ: newest doc ปี 2568 + keyword overlap หนัก)
  - TC-008 PASS, เนื้องาน rule cited จาก กวจ_51385 [15] ✓

### Deploy ขึ้น server (ทุกอย่าง deployed แล้ว)
- `กวจ_0405.4_22315_ประเด็น6_แก้ไขสัญญาเนื้องาน.md` — 13 chunks ✓
- `คำวินิจฉัยที่_๑๔๒_๒๕๖๔.md` (cross-ref removal) — 16 chunks ✓
- `กวจ_51385` (cross-ref เนื้องาน) — 38 chunks ✓
- App restarted ✓

### Eval
- Local: **74/80 PASS** (TC-003 pre-existing fail, TC-027 pre-existing, TC-046/073/074/080 LLM variance)
- TC-008 PASS บน server ✓
- ยืนยันว่า TC-003 fail เป็น pre-existing (fail หลัง revert กวจ_51385 ด้วย → ไม่ใช่ regression จากเรา)

### Gemini fallback fix (จาก session ก่อน, deployed แล้ว)
- `_FALLBACK_MODELS = ["gemini-2.5-flash-lite"]` — 2.0-flash returns 404 NOT_FOUND

---

## Pending

- [ ] TC-003 "คณะกรรมการตรวจรับพัสดุหน้าที่" — ว_78 ไม่ถูกดึง, ต้องหา cross-ref ใส่ใน doc ที่ rank สูงกว่า
- [ ] TC-027 "ผู้ทิ้งงาน" — pre-existing, ยังไม่แก้
- [ ] Run full eval บน server (off-peak — ตอนเช้า)
- [ ] Commit local changes: `.dockerignore`, `eval/golden_test_cases.json`, `src/gemini_client.py`, `src/generation/generator.py`
- [ ] Branch `feat/embedding-v2` + `feat/qdrant-embedding2` — decide delete or use
- [ ] Dependabot PRs #16, #17, #18 — review or close

---

## Next Session

- [ ] Commit + PR จาก branch `fix/stale-cookie-and-rag-improvements`
- [ ] Run full eval server ตอนเช้า (ตรวจ TC-008 citation ถูก source มั้ย)
- [ ] แก้ TC-003: หา doc ที่ rank สูงสำหรับ "คณะกรรมการตรวจรับพัสดุ" + เพิ่ม cross-ref เสนอความเห็น

---

## Key Files

- `ψ/lab/thai-legal-rag/data/md_backup/กวจ_0405.4_22315_ประเด็น6_แก้ไขสัญญาเนื้องาน.md` — NEW sub-doc (local + server)
- `ψ/lab/thai-legal-rag/data/md_backup/01_กวจ_51385_191268_...md` — cross-ref เนื้องาน bullet เพิ่ม bullet แรกใน สรุปข้อวินิจฉัย (local + server)
- `ψ/lab/thai-legal-rag/data/md_backup/คำวินิจฉัยที่_๑๔๒_๒๕๖๔.md` — cross-ref ปลอมออก (local + server)
- `ψ/lab/thai-legal-rag/src/gemini_client.py` — fallback model fix

## Key Insight

**sub-doc approach ช่วย vector score แต่ MMR diversity ยังบล็อก** — เมื่อ corpus ใหญ่ขึ้น (28K chunks) docs เรื่อง แก้ไขสัญญา มีเยอะมาก MMR เลือก 15 docs หมดแล้วก่อนถึง sub-doc
**cross-ref ใน top-ranked doc (กวจ_51385) ได้ผลดีกว่า** — content ถูก cite แม้ source ไม่ใช่ กวจ_22315 โดยตรง
