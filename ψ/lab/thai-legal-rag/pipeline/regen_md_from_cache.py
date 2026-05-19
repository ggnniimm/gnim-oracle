#!/usr/bin/env python3
"""Regenerate MD from existing raw_cache (no re-download, no re-extract)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.drive import stream_pdf
from src.ingestion.ocr import pdf_to_markdown

TARGET_FILES = [
    {
        "file_id": "1orhfV8VCCs3-jKe31nP6iwUTfwr_tO-c",
        "filename": "01_กวจ_ว298_270469_แนวทางปฏิบัติในการอุทธรณ์ผ่านระบบอิเล็กทรอนิกส์.pdf",
    },
]

for item in TARGET_FILES:
    fid = item["file_id"]
    fname = item["filename"]
    print(f"[{fname}] Downloading PDF...")
    pdf_bytes = stream_pdf(fid)
    print(f"  {len(pdf_bytes):,} bytes — re-structuring from raw_cache (force=True, per_page=True)...")
    result = pdf_to_markdown(pdf_bytes, file_id=fid, filename=fname, force=True, per_page=True, page_delay=0)
    remaining = result["text"].count("extraction failed")
    print(f"  Done: {len(result['text']):,} chars, remaining failures: {remaining}")
