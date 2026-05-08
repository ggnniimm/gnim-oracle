# Handoff: Thai Legal RAG — Government Gazette Q&A Analysis

📡 **Session**: dc8047b8 | gnim-oracle | ~15m
**Date**: 2026-05-06 19:35  
**Context**: Explored Government Gazette documents (กวจ) in RAG to analyze Ming's procurement law question

---

## What We Did

- **Located 3 Government Gazette documents** in `data/md_backup/`:
  - ✅ กวจ 2610 (4 files found with this issue number)
  - ✅ กวจ 3061 — Contract amendment from fixed-price to price-adjustment (K value)
  - ✅ กวจ 30307 — Request to NOT receive advance payment

- **Read and summarized 2 key documents**:
  - **กวจ 3061** (2024-01-24): Amendment to construction contract — can amend if state benefit
  - **กวจ 30307** (2021-07-08): Advance payment waiver — can change terms BEFORE signing (exemption case)

- **Analyzed Ming's Question**: "ผู้รับจ้างไม่เบิกเงินล่วงหน้า ต้องแก้ไขสัญญาหรือไม่?"
  - Mapped 2 scenarios: before vs after contract signing
  - Cross-referenced both documents to show legal path for each case
  - Identified key principle: **Before signing = change terms freely | After signing = requires exemption**

---

## Pending

- [ ] **User Ming to provide specific scenario context** — is contractor requesting waiver before or after contract signature?
- [ ] Cross-ref check: verify if มาตรา 97 exceptions apply (state benefit / no loss to state)
- [ ] Optional: trace if any procurement disputes in RAG relate to advance payment waiver + amendment combo

---

## Next Session

- [ ] **If Ming clarifies scenario** → dig deeper into relevant document (กวจ 30307 for pre-sign, กวจ 3061 for post-sign amendment)
- [ ] **Consider adding new analysis doc** — create summary guide linking both กวจ for "advance payment waiver + contract lifecycle" pattern
- [ ] **Check if Ming wants PDF file import** — User asked about `กวจ_2610_20012565` file from Downloads (not yet in RAG)
- [ ] **Monitor for eval regressions** — recent Vertex AI batch embed fix (commit 55ae882) — next full eval needed

---

## Key Files Reviewed

- `ψ/lab/thai-legal-rag/data/md_backup/01_กวจ_3061_240167_ข้อหารือสัญญาก่อสร้าง...md` (67 lines)
- `ψ/lab/thai-legal-rag/data/md_backup/01_กวจ_30307_080764_ข้อหารือการขอไม่รับเงินล่วงหน้า.md` (67 lines)

---

## Pending External File

- `Downloads/กวจ_2610_20012565_การจ่ายเงินล่วงหน้าและการคืนหลักประกันและการแก้ไขสัญญา.pdf`
  - User asked: "Is this in RAG?" → **No** (not found in data/md_backup)
  - **Drive file_id**: `1XAQGhkT-UD3U7DWjudrdcFsnWgUJFP5e`
  - **Drive URL**: https://drive.google.com/file/d/1XAQGhkT-UD3U7DWjudrdcFsnWgUJFP5e/view
  - Status: **Deferred** — import to RAG later (OCR → MD → re-index)
