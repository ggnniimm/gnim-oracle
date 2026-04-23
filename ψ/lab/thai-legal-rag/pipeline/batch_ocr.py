#!/usr/bin/env python3
"""
Batch OCR — download PDFs from Google Drive folder and save as markdown files.
OCR only, no indexing.

Usage:
    python batch_ocr.py --folder-id DRIVE_FOLDER_ID --output-dir data/md_ac
    python batch_ocr.py --env-key DRIVE_FOLDER_AC --output-dir data/md_ac
    python batch_ocr.py --env-key DRIVE_FOLDER_AC --output-dir data/md_ac --limit 5
"""
import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from tqdm import tqdm

from src.ingestion.drive import list_files, stream_pdf
from src.ingestion.ocr import pdf_to_markdown

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description="Batch OCR — Drive PDFs to Markdown")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--folder-id", help="Google Drive folder ID")
    g.add_argument("--env-key", help="Env var name containing folder ID (e.g. DRIVE_FOLDER_AC)")
    p.add_argument("--output-dir", required=True, help="Directory to save .md files")
    p.add_argument("--limit", type=int, default=0, help="Max files to process (0=all)")
    p.add_argument("--skip-existing", action="store_true", default=True,
                   help="Skip files that already exist in output dir (default: True)")
    return p.parse_args()


def sanitize_filename(name: str) -> str:
    """Convert PDF filename to safe .md filename."""
    stem = name.rsplit(".", 1)[0] if "." in name else name
    # Replace spaces and problematic chars
    safe = stem.replace(" ", "_").replace("/", "_").replace("\\", "_")
    return f"{safe}.md"


def main():
    args = parse_args()

    load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

    folder_id = args.folder_id or os.getenv(args.env_key)
    if not folder_id:
        logger.error(f"Folder ID not found (env key: {args.env_key})")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Listing files in folder: {folder_id}")
    files = list_files(folder_id)
    pdf_files = [f for f in files if f["name"].lower().endswith(".pdf")]
    logger.info(f"Found {len(pdf_files)} PDF files")

    if args.limit > 0:
        pdf_files = pdf_files[:args.limit]
        logger.info(f"Limited to {len(pdf_files)} files")

    # Check existing
    if args.skip_existing:
        existing = {p.name for p in output_dir.glob("*.md")}
        to_process = []
        for f in pdf_files:
            md_name = sanitize_filename(f["name"])
            if md_name in existing:
                continue
            to_process.append(f)
        skipped = len(pdf_files) - len(to_process)
        if skipped:
            logger.info(f"Skipping {skipped} already OCR'd files")
        pdf_files = to_process

    if not pdf_files:
        logger.info("Nothing to process!")
        return

    success = 0
    failed = []

    for fi in tqdm(pdf_files, desc="OCR", unit="file"):
        file_id = fi["id"]
        file_name = fi["name"]
        md_name = sanitize_filename(file_name)
        out_path = output_dir / md_name

        try:
            pdf_bytes = stream_pdf(file_id)
            result = pdf_to_markdown(pdf_bytes, file_id=file_id, filename=file_name)
            text = result.get("text", "")

            if not text.strip():
                logger.warning(f"Empty OCR result: {file_name}")
                failed.append(file_name)
                continue

            out_path.write_text(text, encoding="utf-8")
            success += 1
            logger.info(f"OK: {file_name} → {md_name} ({len(text)} chars)")

        except Exception as e:
            logger.error(f"FAIL: {file_name} — {e}")
            failed.append(file_name)

    print(f"\n{'='*60}")
    print(f"Done: {success} OK, {len(failed)} failed, {len(pdf_files)} total")
    if failed:
        print(f"\nFailed files:")
        for f in failed:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
