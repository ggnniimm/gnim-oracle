#!/usr/bin/env python3
"""
Batch 5: Re-OCR all flash-era MDs with quality: low or quality: review-needed.

Unlike reocr_circulars_pro.py (which targets หนังสือเวียน only), this script
targets any doc_type where the flash OCR flagged quality problems.

Resume-safe: at startup, skips files that now show ocr_engine != gemini-2.0-flash
OR quality == good. Restart freely after interruption.

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/batch5_reocr_quality.py
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/batch5_reocr_quality.py --dry-run
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/batch5_reocr_quality.py --limit 3
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
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

_FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _fm(text: str, field: str) -> str:
    m = _FM_RE.match(text)
    if not m:
        return ""
    for line in m.group(1).splitlines():
        if line.startswith(f"{field}:"):
            return line[len(f"{field}:"):].strip().strip('"')
    return ""


def collect_targets(md_dir: Path) -> list[dict]:
    targets = []
    for md_path in sorted(md_dir.glob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        quality = _fm(text, "quality")
        if quality not in ("low", "review-needed"):
            continue
        ocr_engine = _fm(text, "ocr_engine")
        # Target: flash-era or pre-pipeline (no engine field)
        if ocr_engine not in ("gemini-2.0-flash", ""):
            continue
        status = _fm(text, "status")
        if status == "inactive":
            continue
        file_id = _fm(text, "file_id")
        if not file_id:
            logger.warning(f"No file_id in {md_path.name} — skipping")
            continue
        original_filename = _fm(text, "original_filename") or md_path.stem + ".pdf"
        page_count_str = _fm(text, "page_count")
        page_count = int(page_count_str) if page_count_str.isdigit() else 0
        targets.append({
            "md_path": md_path,
            "file_id": file_id,
            "original_filename": original_filename,
            "page_count": page_count,
            "quality": quality,
            "doc_type": _fm(text, "doc_type"),
        })
    return targets


def ocr_with_retry(pdf_bytes, file_id, filename, per_page, page_delay, max_retries=3):
    delays = [30, 60, 120]
    for attempt in range(max_retries + 1):
        try:
            return pdf_to_markdown(
                pdf_bytes, file_id=file_id, filename=filename,
                force=True, per_page=per_page, page_delay=page_delay,
            )
        except Exception as e:
            if attempt < max_retries:
                wait = delays[min(attempt, len(delays) - 1)]
                logger.warning(f"  attempt {attempt+1} failed: {e} — retrying in {wait}s")
                time.sleep(wait)
            else:
                raise


def parse_args():
    p = argparse.ArgumentParser(description="Batch 5: re-OCR quality:low/review-needed flash MDs")
    p.add_argument("--limit", type=int, default=0, help="Max files to process (0=all)")
    p.add_argument("--dry-run", action="store_true", help="List targets only, no OCR")
    p.add_argument("--delay", type=float, default=10.0, help="Seconds between docs (default 10s)")
    p.add_argument("--page-delay", type=float, default=5.0, help="Seconds between pages (default 5s)")
    return p.parse_args()


def main():
    args = parse_args()
    targets = collect_targets(MD_BACKUP_DIR)
    logger.info(f"Found {len(targets)} targets")

    if args.dry_run:
        for t in targets:
            print(f"  [{t['quality']:14s}] {t['page_count']:>3}p  {t['doc_type']:20s}  {t['md_path'].name}")
        return 0

    limit = args.limit if args.limit > 0 else len(targets)
    done, failed = 0, []

    for i, t in enumerate(targets[:limit], 1):
        logger.info(
            f"[{i}/{min(limit, len(targets))}] {t['md_path'].name} "
            f"({t['page_count']}p, {t['quality']})"
        )
        try:
            pdf_bytes = stream_pdf(t["file_id"])
            result = ocr_with_retry(
                pdf_bytes, t["file_id"], t["original_filename"],
                per_page=True, page_delay=args.page_delay,
            )
            new_quality = re.search(r'quality:\s*"([^"]+)"', result["text"])
            q = new_quality.group(1) if new_quality else "?"
            logger.info(f"  ✓ {result['doc_type']} | {len(result['text']):,} chars | quality: {q}")
            done += 1
        except Exception as e:
            logger.error(f"  ✗ FAILED: {e}")
            failed.append(t["md_path"].name)

        if i < min(limit, len(targets)) and args.delay > 0:
            time.sleep(args.delay)

    logger.info(f"\nDone: {done}/{min(limit, len(targets))} | Failed: {len(failed)}")
    for f in failed:
        logger.info(f"  FAILED: {f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
