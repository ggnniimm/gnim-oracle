# Handoff: Re-OCR Batch 4 — Per-Page Pro Pipeline

**Date**: 2026-05-10 22:35
**Context**: ~85%

## Context
**Oracle**: Gnim | **Human**: Ming

## What We Did

### Pipeline Upgrades (src/ingestion/ocr.py)
- **OCR location split**: Added `OCR_LOCATION = "us-central1"` (separate from `global` for embedding). New `get_ocr_client()` in `gemini_client.py`. All OCR calls now hit us-central1 quota pool.
- **PNG 300 DPI extraction**: Replaced PDF-fragment path with `_pdf_pages_to_images()` using pymupdf/fitz — renders each page at 300 DPI RGB PNG before sending to Pro.
- **Per-page mode**: `extract(per_page=True)` — Pro extracts each page verbatim → Pro structures full raw text → Flash anchor. `pdf_to_markdown()` and `reocr_circulars_pro.py` both support `--per-page --page-delay` flags.
- **Raw cache resume**: On retry, loads `ocr_cache/{hash}_raw.json` and resumes from the first unextracted page (skips already-done pages). Saves ~70 min when retrying a 71-page file.
- **Token limit guard**: Truncates `raw_text` to 150K chars (~62K tokens) before structure call to avoid Vertex AI's 65,536 input token limit.
- **OCR prompt improvements from EXPERT_OCR_SOP.md**: page context header (หน้าที่ N/total), confusion matrix (๒/๖, ๔/๕/๙, ๘/๓), `<!-- Page N -->` markers.

### Root Cause of Prior 429s
Old batches 1-3 used `GOOGLE_CLOUD_LOCATION=global` for OCR — exhausted `global` Pro quota pool. `us-central1` was untouched. Now OCR uses `us-central1` (separate quota from embedding which stays on `global`).

### Batch 4 Run
- Command: `python3 pipeline/reocr_circulars_pro.py --per-page --delay 60`
- 14 files total
- **File 1/14 FAILED** (`01_กวจ_ว125_010366_...md`, 71 pages): structure call (Pro streamGenerateContent) hits 429 mid-stream at ~80s — response too large to stream within per-minute token budget. 4 attempts all failed same way.
- **File 2/14 was in progress** (4 pages, structure call started) when killed
- **Files 3-14**: not processed yet

## Pending

- [ ] Handle ว125 (file 1/14) separately — raw cache complete at `data/ocr_cache/8329dda1c9d60a4d_raw.json` (388 KB, all 71 pages). Need to split structure call into two halves or use non-streaming `generate_content` to avoid mid-stream 429.
- [ ] Restart batch 4 for files 2-14 (file 2 was killed mid-structure, will retry automatically)
- [ ] After batch done: rsync `md_backup/` to prod `root@31.97.188.155:/app/thai-legal-rag/data/md_backup/`
- [ ] Force-reindex on prod for changed files
- [ ] Run full 84-TC eval to lock baseline

## Next Session

- [ ] `tail -50 /tmp/reocr_batch4.log` — check what was done before kill
- [ ] Fix ว125: write a one-off script that loads raw_cache, splits pages 1-35 / 36-71, calls structure twice with `generate_content` (non-streaming), merges sections, saves MD
- [ ] Restart batch: `THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/reocr_circulars_pro.py --per-page --delay 60 >> /tmp/reocr_batch4b.log 2>&1 &`
- [ ] Consider: for very large docs (>50 pages), auto-detect and split structure call into halves in ocr.py

## Key Files

- `src/ingestion/ocr.py` — per-page extraction, cache resume, token truncation (modified, uncommitted)
- `src/gemini_client.py` — `get_ocr_client()` us-central1 (committed)
- `src/config.py` — `OCR_LOCATION` (committed)
- `data/ocr_cache/8329dda1c9d60a4d_raw.json` — ว125 raw 71 pages (ready to structure)
- `data/md_backup/01_กวจ_ว125_010366_การแก้ไขเพิ่มเติมเงื่อนไขในแบบประก.md` — old flash OCR still intact
- `/tmp/reocr_batch4.log` — full batch log
