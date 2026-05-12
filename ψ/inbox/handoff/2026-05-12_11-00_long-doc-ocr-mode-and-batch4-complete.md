# Handoff: Long-doc OCR mode + batch 4 complete

📡 Session: 1b65ad2d | gnim-oracle | ~26h elapsed
**Date**: 2026-05-12 11:00
**Context**: ~70%

## Context
**Oracle**: Gnim | **Human**: Ming

## What We Did

### 1. Long-doc OCR mode (`feat(ocr)` — commit 283c72c, pushed)

Old per-page pipeline asked Pro to verbatim-copy 70+ pages into a fixed 4-section template
(หลักการ/แนวปฏิบัติ/การใช้บังคับ/ข้อสังเกต). For long circulars (ว125 71 pages, ว647 75 pages,
ว1203 77 pages) this consistently blew up — streaming 429 mid-stream at ~80s, non-streaming
ReadTimeout past 600s.

New `_structure_long_doc()` in `src/ingestion/ocr.py` (triggers when `page_count > 20`):
1. **One small Pro call** asks for JSON `{frontmatter, chapters: [{heading, start_page, end_page}]}` —
   small output, ~55-95s.
2. **Body assembled in Python** by slicing `raw_pages` per chapter range. Byte-identical to raw
   extraction; `<!-- Page N -->` markers preserved inside each chapter.
3. **Safety net**: if outline misses any pages, append them under `## ภาคผนวก หน้าที่ไม่ได้จัดเข้าบท`.

### 2. Chapter-aware anchor (same commit)

For docs >25K chars, `generate_anchor()` now uses `_sample_chapters_for_anchor()` —
first 1.5K chars of every `##` section (max 20K total) instead of the first 8K of the doc.
Keywords now cover all chapters, not just the cover letter.

Also separated try/except for keywords vs summary — a summary timeout no longer discards keywords.

### 3. `get_ocr_client(timeout_ms=...)` improvement (`src/gemini_client.py`)

Pass a custom `httpx.Client(timeout=...)` because the SDK's `http_options["timeout"]` is
NOT propagated to the underlying httpx client (verified: httpx client always has
`Timeout(timeout=5.0)` default regardless of http_options). Long-doc outline now uses 600s.

### 4. `pipeline/retry_failed_pages.py` (new utility)

Reads raw_cache, finds entries matching `[หน้า N: (extraction failed|timeout)]` placeholder
pattern, re-renders those PDF pages and re-extracts with 300s timeout. Updates raw_cache
in place, then re-runs `pdf_to_markdown` to regenerate the MD. Used 3 times on ว647 to
recover all 19 originally-failed pages.

### 5. Memory + retro committed (`memory:` — commit 3a0e0fc, pushed)

- `learnings/2026-05-10_streaming-api-200ok-not-success-and-retry-granularity.md`
- `retrospectives/2026-05/10/22.37_reocr-batch4-per-page-pro.md`
- `inbox/handoff/2026-05-10_22-35_reocr-batch4-per-page-pro.md`
- `lab/sample-docs/EXPERT_OCR_SOP.md`
- `lab/sample-docs/ocr_v4.py`

### 6. Re-OCR'd 14 หนังสือเวียน (gemini-2.0-flash → gemini-2.5-pro)

| File | Pages | Chars | Notes |
|---|---|---|---|
| ว125 | 71 | 162K | 5 chapters, quality:review-needed (some OCR issues flagged) |
| ว647 | 75 | 180K | 10 chapters incl. ภาคผนวก ก/ข/ค, all 75 pages recovered via 3 retry rounds |
| ว877 | 4 | 12K | quality:good |
| ว139 | small | 2K | quality:low (many placeholders from API issues during run) |
| ว845 | 26 | 45K | long-doc |
| ว1203 | 77 | 132K | long-doc, succeeded on 3rd outline retry |
| ปรับปรุงบัญชี | small | 4K | quality:good |
| ว418 | 2 | (inactive) | user marked obsolete (official แบบสัญญา now exists) |
| ว809 | 45 | 98K | long-doc |
| ว1288 | 50 | 116K | long-doc |
| ว499 | 54 | 86K | long-doc |
| ว281 | 50 | 70K | long-doc |
| ว225 | — | — | re-OCR'd earlier session |
| หลักเกณฑ์ราคากลาง | 27 | 19K | long-doc, 4 chapters |

### 7. Cleaned up 23 `+/_` filename-collision duplicates in `data/md_backup/`

Old flash MDs used URL-encoded `+` for spaces. New Pro saves use `_` from `original_filename`.
Result: 23 duplicate pairs across the corpus. Deleted all flash `+` versions where Pro `_`
equivalent existed. One legitimate duplicate by file_id remains (`10WpLyz...`:
`กวจ_0405.4_22315_170564_แก้ไขสัญญาเนื้องาน.md` and `กวจ_0405.4_22315_ประเด็น6_...md`) —
both flash, different stems, same Drive ID. Left for human review.

## Pending

- [ ] Rsync `data/md_backup/` to prod (`root@31.97.188.155:/app/thai-legal-rag/data/md_backup/`)
- [ ] Force-reindex changed files on prod Qdrant
- [ ] Run full 84-TC prod eval — verify no regression from 80/84 baseline
- [ ] (Optional) Retry stubborn pages on quality:low MDs (ว139 has many placeholders) via `retry_failed_pages.py`
- [ ] (Optional) Improve `_fix_doc_number_from_filename` regex to handle `ว<NNN>` pattern (currently fails for filenames where the segment after `กวจ` is non-purely-numeric like `ว647`). Affects new long-doc MDs whose source PDF had a `ว`-prefixed segment after `กวจ`.
- [ ] (Optional) Investigate the `10WpLyz...` Drive ID duplicate — two MDs with same file_id but different stems

## Next Session

- [ ] Start with `/recap` to orient
- [ ] Verify current MD state (count distinct file_ids, total chunk count if reindexed locally)
- [ ] Rsync to prod + force-reindex per the [thai-legal-rag deployment notes in MEMORY.md]
- [ ] Decide whether to also re-OCR the remaining 342 `+`-in-name MDs (Drive's actual filenames likely use `+` so these are correct, not duplicates — verify before touching)

## Key Files

- `ψ/lab/thai-legal-rag/src/ingestion/ocr.py` — long-doc mode + chapter-sampling anchor + improved fallback
- `ψ/lab/thai-legal-rag/src/gemini_client.py` — `get_ocr_client(timeout_ms=...)` with custom httpx client
- `ψ/lab/thai-legal-rag/pipeline/retry_failed_pages.py` — utility for recovering failed pages
- `ψ/lab/thai-legal-rag/data/md_backup/` — 14 new Pro MDs from batch 4
- `ψ/memory/learnings/2026-05-10_streaming-api-200ok-not-success-and-retry-granularity.md`

## Commits Pushed (this session)

- `283c72c feat(ocr): long-doc mode for 20+ page circulars` — code changes
- `3a0e0fc memory: 2026-05-10 streaming-API learning + batch 4 handoff/retro`

Both pushed to `origin/main` along with 6 commits from prior session that were also queued
(8 total in the push).
