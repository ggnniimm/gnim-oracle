#!/usr/bin/env python3
"""
Re-OCR all หนังสือเวียน that were OCR'd with gemini-2.0-flash (wrong schema).
Uses the new Pro v2 pipeline: Flash classify → Pro extract → Flash anchor.

Reads file_id + original_filename from existing MD frontmatter, streams PDF
from Google Drive, calls pdf_to_markdown(force=True), auto-saves new MD.

Resume-safe: at startup, only processes files still showing ocr_engine: gemini-2.0-flash.
Restart the script after interruption — already-done files are skipped.

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/reocr_circulars_pro.py
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/reocr_circulars_pro.py --limit 5
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/reocr_circulars_pro.py --dry-run
"""
import argparse
import logging
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from src.config import MD_BACKUP_DIR
from src.ingestion.drive import stream_pdf
from src.ingestion.ocr import pdf_to_markdown

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

_FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _get_frontmatter_field(text: str, field: str) -> str:
    m = _FM_RE.match(text)
    if not m:
        return ""
    fm = m.group(1)
    for line in fm.splitlines():
        if line.startswith(f"{field}:"):
            val = line[len(f"{field}:"):].strip().strip('"')
            return val
    return ""


def collect_targets(md_dir: Path) -> list[dict]:
    """Find all MDs with doc_type=หนังสือเวียน and ocr_engine=gemini-2.0-flash."""
    targets = []
    for md_path in sorted(md_dir.glob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        doc_type = _get_frontmatter_field(text, "doc_type")
        ocr_engine = _get_frontmatter_field(text, "ocr_engine")
        status = _get_frontmatter_field(text, "status")
        if doc_type == "หนังสือเวียน" and ocr_engine == "gemini-2.0-flash" and status != "inactive":
            file_id = _get_frontmatter_field(text, "file_id")
            original_filename = _get_frontmatter_field(text, "original_filename")
            if not file_id:
                logger.warning(f"No file_id in {md_path.name} — skipping")
                continue
            targets.append({
                "md_path": md_path,
                "file_id": file_id,
                "original_filename": original_filename or md_path.stem + ".pdf",
            })
    return targets


def ocr_with_retry(
    pdf_bytes: bytes,
    file_id: str,
    filename: str,
    max_retries: int = 3,
    per_page: bool = False,
    page_delay: float = 3.0,
) -> dict:
    """Call pdf_to_markdown with exponential backoff on any exception."""
    delays = [30, 60, 120]
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return pdf_to_markdown(
                pdf_bytes, file_id=file_id, filename=filename,
                force=True, per_page=per_page, page_delay=page_delay,
            )
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                wait = delays[min(attempt, len(delays) - 1)]
                logger.warning(f"  attempt {attempt+1} failed: {e} — retrying in {wait}s")
                time.sleep(wait)
            else:
                raise last_exc


def parse_args():
    p = argparse.ArgumentParser(description="Re-OCR หนังสือเวียน with Pro v2 pipeline")
    p.add_argument("--limit", type=int, default=0, help="Max files to process (0=all)")
    p.add_argument("--dry-run", action="store_true", help="List targets only, no OCR")
    p.add_argument("--delay", type=float, default=10.0,
                   help="Seconds to wait between docs (default 10s, avoids Pro quota bursts)")
    p.add_argument("--per-page", action="store_true",
                   help="Extract raw text per page with Pro, then structure in one final Pro call. "
                        "Avoids streaming timeout on large PDFs. Uses page_count+1 Pro calls per doc.")
    p.add_argument("--page-delay", type=float, default=15.0,
                   help="Seconds to wait between page extractions in --per-page mode (default 15s)")
    return p.parse_args()


def main():
    args = parse_args()

    md_dir = MD_BACKUP_DIR
    logger.info(f"Scanning {md_dir} for หนังสือเวียน with gemini-2.0-flash ...")
    targets = collect_targets(md_dir)
    logger.info(f"Found {len(targets)} files to re-OCR")

    if args.limit > 0:
        targets = targets[:args.limit]
        logger.info(f"Limited to {len(targets)} files")

    if args.dry_run:
        for t in targets:
            print(f"  {t['md_path'].name}  [{t['file_id']}]")
        print(f"\nTotal: {len(targets)} files (dry-run, nothing processed)")
        return

    success = 0
    failed = []
    start_all = time.time()

    for i, t in enumerate(targets, 1):
        md_path = t["md_path"]
        file_id = t["file_id"]
        filename = t["original_filename"]
        elapsed_total = time.time() - start_all

        logger.info(
            f"[{i}/{len(targets)}] {md_path.name} "
            f"(elapsed {elapsed_total/60:.1f}m)"
        )

        try:
            pdf_bytes = stream_pdf(file_id)
            pdf_size_kb = len(pdf_bytes) / 1024
            logger.info(f"  PDF: {pdf_size_kb:.0f} KB")

            t0 = time.time()
            result = ocr_with_retry(
                pdf_bytes, file_id=file_id, filename=filename,
                per_page=args.per_page, page_delay=args.page_delay,
            )
            ocr_s = time.time() - t0

            doc_type = result.get("doc_type", "?")
            text_len = len(result.get("text", ""))
            logger.info(
                f"  OK: {doc_type} | {text_len} chars | {ocr_s:.0f}s"
            )
            success += 1

        except Exception as e:
            logger.error(f"  FAIL: {e}")
            failed.append(md_path.name)
            # Brief pause after errors before continuing
            time.sleep(5)
            continue

        if i < len(targets) and args.delay > 0:
            time.sleep(args.delay)

    total_time = time.time() - start_all
    print(f"\n{'='*60}")
    print(f"Done: {success} OK  |  {len(failed)} failed  |  {len(targets)} total")
    print(f"Total time: {total_time/60:.1f} min")
    if failed:
        print(f"\nFailed:")
        for f in failed:
            print(f"  - {f}")
    print("\nNext: run full prod eval then push+reindex updated MDs.")


if __name__ == "__main__":
    main()
