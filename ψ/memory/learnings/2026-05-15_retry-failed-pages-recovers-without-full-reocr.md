---
name: retry-failed-pages-recovers-without-full-reocr
description: When Pro OCR leaves a "[หน้า N: extraction failed]" placeholder in raw_cache, retry_failed_pages.py re-OCRs just that page (5min timeout) and regenerates the MD — no need to re-do the whole 19-page doc.
metadata:
  type: feedback
---

**When OCR `quality: review-needed` flags an inferred page, check raw_cache for `[หน้า N: extraction failed]` first — then patch with `retry_failed_pages.py`, don't re-run the whole document.**

**Why:** ว124 re-OCR (19 pages, 24.5 min with Pro per-page) produced `quality: review-needed` with `quality_note: "page 9 missing, inferred from context"`. Inspecting `data/ocr_cache/<hash>_raw.json[8]` showed a 74-char placeholder: `[หน้า 9: extraction failed — The read operation timed out]` — page 9 was a dense table (สิ่งที่ส่งมาด้วย ๓ ตัวอย่างวิธีจัดทำแผนการทำงาน, 9 columns × ~10 rows) that exceeded the 60s default per-page timeout.

`retry_failed_pages.py` is exactly for this: scans raw_cache for the failure regex, re-extracts only those pages with a 5-min timeout (`_RETRY_TIMEOUT_MS = 300_000`), updates the cache in place, then re-runs `pdf_to_markdown(force=True)` which reuses the now-complete cache and regenerates outline + anchor + MD. Total recovery: ~90s for one page vs ~25min for a full re-OCR.

**How to apply:**
1. After any Pro re-OCR, if `quality: review-needed`, inspect raw_cache before assuming the doc is just dense:
   ```bash
   python3 -c "import hashlib,json; h=hashlib.sha256('<file_id>'.encode()).hexdigest()[:16]; print(json.loads(open(f'data/ocr_cache/{h}_raw.json').read())[N-1][:200])"
   ```
2. If you see `[หน้า N: extraction failed ...]`, run:
   ```bash
   THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/retry_failed_pages.py \
     --file-id <FILE_ID> --filename "<original_filename>.pdf"
   ```
3. Verify result: `quality: good`, `quality_note: ""`, chunk count likely increases meaningfully (ว124: 66 → 118 chunks, +78%, after p9 table was recovered).

**Related:** [[raw-cache-complete-does-not-mean-valid]] — placeholder-poisoned cache silently passes the "complete" check, so the retry script is the safe path; manually deleting the cache and re-running would re-OCR all pages (slow and wasteful when only one failed).
