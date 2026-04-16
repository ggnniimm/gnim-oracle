---
title: ## MD Files in md_backup Contain AI-Generated Content
tags: [md-files, ai-summaries, ocr, thai-legal, data-quality]
created: 2026-04-14
source: Thai Legal RAG 2026-03-22
---

# ## MD Files in md_backup Contain AI-Generated Content

## MD Files in md_backup Contain AI-Generated Content

The OCR'd MD files in `data/md_backup/` are NOT pure verbatim transcriptions. They contain AI-generated sections:
- `## สรุปข้อวินิจฉัย` — bullet-point summary created by AI, not in original
- `## บทสรุปสำหรับสืบค้น` — keyword blob for search, not in original
- `## ประเด็นข้อหารือ (ไม่มีส่วนนี้ในเอกสาร)` — template placeholder

Missing from originals: letterhead (ด่วนที่สุด, เลขที่), signature blocks, contact information.

**Impact**: AI summaries helpful for RAG retrieval. But for legal accuracy verification, must re-OCR from source PDF using `stream_pdf(file_id)` + Gemini verbatim OCR.

**Verified on**: ว159 TOR — re-OCR revealed full letterhead and signature missing from MD.

---
*Added via Oracle Learn*
