#!/usr/bin/env python3
"""
Retry per-page OCR for pages that previously failed (placeholders in raw_cache).

Reads the raw_cache JSON for a given file_id, finds entries matching the
"[หน้า N: extraction failed —" or "[หน้า N: timeout]" placeholder pattern,
re-renders those PDF pages and re-runs Pro extraction on each one with a
longer timeout. Updates raw_cache in place, then re-runs pdf_to_markdown
to regenerate the MD with the new content.

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/retry_failed_pages.py \\
        --file-id 1u5C-XVte7gh0cpBQKVYWipTFTzUlbzN- \\
        --filename "กวจ_ว647_250968_แนวทางปฏิบัติสำหรับการจ้างทำของ.pdf"
"""
import argparse
import hashlib
import json
import logging
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from google.genai import types as genai_types

from src.config import OCR_CACHE_DIR, OCR_EXTRACT_MODEL
from src.ingestion.drive import stream_pdf
from src.ingestion.ocr import (
    _EXTRACT_PAGE_RAW_PROMPT_TEMPLATE,
    _pdf_pages_to_images,
    pdf_to_markdown,
)
from src.gemini_client import get_ocr_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_FAILURE_RE = re.compile(r"\[หน้า \d+: (?:extraction failed|timeout)")
_RETRY_TIMEOUT_MS = 300_000  # 5 min per page — generous for stubborn pages


def parse_args():
    p = argparse.ArgumentParser(description="Retry failed pages in raw_cache")
    p.add_argument("--file-id", required=True)
    p.add_argument("--filename", required=True)
    p.add_argument("--delay", type=float, default=5.0,
                   help="Seconds between retries (default 5s)")
    return p.parse_args()


def main():
    args = parse_args()
    file_id = args.file_id
    filename = args.filename

    cache_hash = hashlib.sha256(file_id.encode()).hexdigest()[:16]
    raw_cache_path = OCR_CACHE_DIR / f"{cache_hash}_raw.json"
    if not raw_cache_path.exists():
        logger.error(f"No raw_cache found at {raw_cache_path}")
        return 1

    raw_pages = json.loads(raw_cache_path.read_text(encoding="utf-8"))
    failed_indexes = [i + 1 for i, p in enumerate(raw_pages) if _FAILURE_RE.search(p)]
    if not failed_indexes:
        logger.info("No failed pages in raw_cache — nothing to retry")
        return 0

    logger.info(f"Found {len(failed_indexes)} failed pages: {failed_indexes}")

    logger.info(f"Downloading PDF: {file_id}")
    pdf_bytes = stream_pdf(file_id)
    page_images = _pdf_pages_to_images(pdf_bytes)
    total_pages = len(page_images)
    if total_pages != len(raw_pages):
        logger.error(
            f"Page count mismatch: cache has {len(raw_pages)} pages, "
            f"PDF has {total_pages}"
        )
        return 1

    ocr_client = get_ocr_client(timeout_ms=_RETRY_TIMEOUT_MS)
    successes = 0
    still_failed: list[int] = []

    for n, page_num in enumerate(failed_indexes, 1):
        img_bytes = page_images[page_num - 1]
        logger.info(
            f"[{n}/{len(failed_indexes)}] Re-extracting page {page_num}/{total_pages} "
            f"({len(img_bytes)//1024} KB)"
        )
        page_prompt = _EXTRACT_PAGE_RAW_PROMPT_TEMPLATE.format(
            page_num=page_num, total_pages=total_pages,
        )
        img_part = genai_types.Part.from_bytes(data=img_bytes, mime_type="image/png")
        try:
            resp = ocr_client.models.generate_content(
                model=OCR_EXTRACT_MODEL,
                contents=[page_prompt, img_part],
            )
            page_text = (resp.text or "").strip()
            if page_text and page_text != "---BLANK---":
                raw_pages[page_num - 1] = f"<!-- Page {page_num} -->\n{page_text}"
                logger.info(f"    Page {page_num} ✓ {len(page_text):,} chars")
                successes += 1
            elif page_text == "---BLANK---":
                raw_pages[page_num - 1] = f"<!-- Page {page_num} -->\n"
                logger.info(f"    Page {page_num} ✓ blank")
                successes += 1
            else:
                logger.warning(f"    Page {page_num} returned empty")
                still_failed.append(page_num)
        except Exception as e:
            logger.warning(f"    Page {page_num} failed again: {e}")
            still_failed.append(page_num)

        # Persist after every page
        raw_cache_path.write_text(
            json.dumps(raw_pages, ensure_ascii=False), encoding="utf-8"
        )

        if n < len(failed_indexes) and args.delay > 0:
            time.sleep(args.delay)

    logger.info(
        f"Retry summary: {successes}/{len(failed_indexes)} recovered, "
        f"{len(still_failed)} still failed"
    )
    if still_failed:
        logger.info(f"Still failed pages: {still_failed}")

    # Re-run pdf_to_markdown — raw_cache is now updated, will skip page extraction
    # and regenerate the MD (outline + anchor + save).
    logger.info("Re-running pdf_to_markdown to regenerate MD ...")
    result = pdf_to_markdown(
        pdf_bytes, file_id=file_id, filename=filename,
        force=True, per_page=True, page_delay=0.0,
    )
    logger.info(f"DONE: {result['doc_type']} | {len(result['text']):,} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
