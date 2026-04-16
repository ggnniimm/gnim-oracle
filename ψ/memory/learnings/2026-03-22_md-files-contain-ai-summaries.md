---
name: md-files-contain-ai-summaries
description: Existing MD files in md_backup mix verbatim OCR with AI-generated summaries — not pure source text
type: learning
date: 2026-03-22
---

# MD Files Contain AI-Generated Content

The OCR'd MD files in `data_with_ac/md_backup/` are NOT pure verbatim transcriptions. They contain:

1. **AI-generated sections**:
   - `## สรุปข้อวินิจฉัย` — bullet-point summary created by AI, not in original
   - `## บทสรุปสำหรับสืบค้น` — keyword blob for search, not in original
   - `## ประเด็นข้อหารือ (ไม่มีส่วนนี้ในเอกสาร)` — template placeholder

2. **Missing from originals**:
   - Letterhead (ด่วนที่สุด, เลขที่, etc.)
   - Signature blocks
   - Contact information

**Impact**: For RAG retrieval, the AI summaries are actually helpful (keywords, structured summary). But for legal accuracy verification, must re-OCR from source PDF. Use `stream_pdf(file_id)` from `drive.py` + Gemini verbatim OCR.

**Verified on**: ว159 TOR — re-OCR revealed full letterhead and signature that were missing from MD.
