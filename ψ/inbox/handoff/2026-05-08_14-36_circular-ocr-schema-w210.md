# Handoff: Circular OCR Schema + Re-OCR ว210

📡 Session: bab1062b | gnim-oracle | thai-legal-rag

**Date**: 2026-05-08 14:36
**Branch**: main (uncommitted changes pending)

## Context
**Oracle**: Gnim | **Human**: Ming
**Focus**: หนังสือเวียน (circular) OCR pipeline — was wedged into ข้อหารือ schema, leaving empty `## ประเด็นข้อหารือ` and broken markdown tables. Used ว ๒๑๐ as guinea pig for new pipeline + format.

## What We Did

### 1. Refactored OCR pipeline for doc-type-aware section schemas
File: `ψ/lab/thai-legal-rag/src/ingestion/ocr.py` (uncommitted)

- **NEW** `_SECTION_TEMPLATES` dict — separate Markdown body schemas for `Ruling_Committee` / `Ruling_AttorneyGeneral` / `Ruling_Court` / `Circular` / `default`
- **NEW** `_CIRCULAR_SECTIONS`: `## หลักการและที่มา` / `## แนวปฏิบัติ` / `## การใช้บังคับ` / `## ข้อสังเกต` (replaces ill-fitting ข้อหารือ template)
- `_EXTRACT_PROMPT_TEMPLATE` now takes `{section_template}` placeholder; added rules: tables max 4 dashes per column, no dot-leader/`*` for blank fields
- `_CLASSIFY_PROMPT` rewritten — explicit Circular criteria (doc_number contains "ว", subject like "แนวทางปฏิบัติ"/"ยกเว้น", has "การใช้บังคับ"). Decision rule: "if doc_number has ว → Circular"
- **NEW** filename safety net in `pdf_to_markdown()`: if filename matches `_ว\d+_` and classifier returned non-Circular, force `doc_type=Circular`
- **NEW** `_normalize_tables()`: regex-collapse `-{5+}` → `----` (kills runaway separators that ballooned ว210 file from 5pp → 25k tokens)
- **REPLACED** `_upload_pdf()` (AI-Studio-only) → `_pdf_part()` using `Part.from_bytes()` (works on Vertex)

### 2. Re-OCR'd ว ๒๑๐ as guinea pig
- Downloaded PDF from Drive (`stream_pdf()`, file_id `1NixH_IpSQVB5PwEdOfzc7Xd1l3Z6uYZp`, 2 MB, 5 pages)
- First OCR: classifier mis-routed to `Ruling_Committee` (because issuer is กวจ.) → fixed prompt + filename override
- Second OCR: `doc_type=หนังสือเวียน` ✓, sections match new schema, tables clean, no broken `:----...` separators
- Anchor (`## บทสรุปสำหรับสืบค้น`) generated after 2 retries (Vertex 429 throttle)
- File: `ψ/lab/thai-legal-rag/data/md_backup/01_กวจ_ว210_240369_การอนุมัติยกเว้นการปฏิบัติตามระเบียบฯ+ข้อ+46+ข้อ+47+และข้อ+52.md`

### 3. Re-indexed in local Qdrant
- Cleared 92 stale duplicates (force-reindex didn't dedup properly via `source_name` filter mismatch — old PDF name vs new MD), deleted dedup entries by file_id
- Fresh index: **46 chunks** (vs 26 in old broken version)
  - หลักการและที่มา: 9, แนวปฏิบัติ: 29, การใช้บังคับ: 3, ข้อสังเกต: 1, anchor: ~3, header: 1
- Local total: 27,959 chunks

### 4. Spot test (4 queries, top-10 retrieval)

| Query | ว210 rank |
|---|---|
| ว 210 กำหนดอย่างไรเกี่ยวกับการรับฟังความคิดเห็น | **#1** ✓ |
| การยกเว้นข้อ 46 47 52 มีผลบังคับใช้เมื่อใด | #8 (was: not in top-10) |
| ผู้ประกอบการสอบถามรายละเอียดผ่านช่องทางใดได้บ้าง | **#1** ✓ |
| หนังสือเวียน ว 210 บังคับใช้ตั้งแต่วันที่เท่าไหร่ | **#1** ✓ |

Q2 still loses to ว ๒๖๐ — that doc also references ข้อ 46/47/52. Cross-ref injection could pin Q2 to ว210 if needed.

## Pending

- [ ] **Eval gate (84-TC) ยังไม่ได้รัน** — Vertex 429 throttle ทำให้ทั้ง local และ prod eval อาจช้า/ล้ม. ผู้ใช้กดถามให้ clarify ก่อนว่าจะไป path ไหน — ยังไม่มีคำตอบสุดท้าย
- [ ] **Deploy ว210 MD ไป prod** — ยังอยู่บน local เท่านั้น
- [ ] **Commit `src/ingestion/ocr.py`** — ยัง uncommitted (work-in-progress, ยังไม่ผ่าน eval)
- [ ] **Cleanup dead imports** — `tempfile`, `os`, `time` ที่ ocr.py ไม่ใช้แล้ว (ลบ `_upload_pdf` ออก)
- [ ] **Untracked vault files** — `ψ/memory/learnings/2026-05-08_docker-compose-restart-vs-up-d.md` + `ψ/memory/retrospectives/2026-05/08/` (carried over from previous session)

## Out of Scope (Future Work)

- **Batch re-OCR 240 หนังสือเวียนเก่า** — ผู้ใช้เลือก "Hybrid" scope (pipeline fix + ว210 only). รอประเมินผลจาก ว210 1-2 สัปดาห์ก่อนตัดสินใจ
- **Q2 cross-ref injection** — ถ้าอยากให้ Q2 ติด #1 ต้องเพิ่ม content ของ ว210 ลงใน สรุปข้อวินิจฉัย ของ ว260 (top-ranked doc)
- **Court judgment template** — `Ruling_Court` มี template ใหม่แล้ว แต่ยังไม่ได้ทดสอบกับเอกสารจริง

## Next Session

- [ ] ตัดสินใจ: prod deploy + prod eval, หรือ local eval ก่อน?
- [ ] ถ้า prod: scp MD → prod, force re-index, run prod eval (target ≥80/84)
- [ ] ถ้า eval pass → commit ocr.py + handoff in commit message
- [ ] ถ้า eval regress → rollback (ไฟล์เก่ายังอยู่ใน git, OCR cache ที่ data/ocr_cache/ มี backup ถ้าต้องการ)
- [ ] (Optional) ลอง Q2 ใหม่หลัง prod deploy — บางทีอันดับเปลี่ยน

## Key Files

- **Code change**: `ψ/lab/thai-legal-rag/src/ingestion/ocr.py` (uncommitted)
- **Re-OCR'd MD**: `ψ/lab/thai-legal-rag/data/md_backup/01_กวจ_ว210_240369_การอนุมัติยกเว้นการปฏิบัติตามระเบียบฯ+ข้อ+46+ข้อ+47+และข้อ+52.md`
- **Plan**: `~/.claude/plans/ocr-bright-lagoon.md`
- **Source PDF (temporary)**: `/tmp/w210.pdf` — re-download via `stream_pdf('1NixH_IpSQVB5PwEdOfzc7Xd1l3Z6uYZp')` if needed

## Environment Notes (carry-over from MEMORY.md)

- Local Qdrant: `QDRANT_URL=http://localhost:6333`, collection `thai_legal_rag` (dim 3072), embedding `gemini-embedding-2` GA on `location=global`
- Vertex AI active: `gen-lang-client-0136329629`. **AI Studio API key dead** (rotated 2026-05-08 leak audit) — OCR must use Vertex via inline-data
- Vertex `gemini-2.5-flash` was throttling badly during this session — anchor generation took 3 retries. Quota may need a wait window before bulk eval
- Prod: `root@31.97.188.155`, container `thai-legal-rag-app-1`. SSH port 22 may be ISP-blocked → use hotspot
