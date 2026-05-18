#!/usr/bin/env python3
"""
Re-OCR specific target files using the Pro v2 pipeline.

Usage:
    cd ψ/lab/thai-legal-rag
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/reocr_target_files.py
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/reocr_target_files.py --dry-run
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/reocr_target_files.py --per-page --limit 3
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

TARGET_FILES = [
    "ว_239.md",       # inactive → will become active after re-OCR
    "ว_296.md",
    "ว_476_300962_ซ้อมความเข้าใจผู้มีอำนาจอนุมัติแก้ไขสัญญา.md",
    "ว+171.md",
    "ว+214.md",
    "ว+377.md",
    "ว54.md",
    "ว83.md",
    "ว94_29-08-2562_การกันเงินกรณีอยู่ระหว่างอุทธรณ์.md",
    "ว94.md",
    "ว115.md",
    "ว119_07-03-2561.md",
    "ว122.md",
    "ว151.md",
    "ว164.md",
    "ว191.md",
    "ว206_ลว.010562_คู่มือ_เปรียบเทียบ_ล่าสุด.md",
    "ว332.md",
    "ว381.md",
    "ว423.md",
    "ว452_28-11-2560.md",
    "ว553.md",
    "ว581+การพิจารณาคุณสมบัติของผู้ยื่นข้อเสนอที่เป็นกิจการร่วมค้า.md",
    "ว582.md",
    "เวียน+290+ตัวอย่างหนังสือค้ำประกัน.md",
    "หนังสือเวียน++ว52.md",
]

_FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def get_field(text: str, field: str) -> str:
    m = _FM_RE.match(text)
    if not m:
        return ""
    for line in m.group(1).splitlines():
        if line.startswith(f"{field}:"):
            return line[len(f"{field}:"):].strip().strip('"')
    return ""


def collect_targets(md_dir: Path) -> list[dict]:
    targets = []
    for fname in TARGET_FILES:
        p = md_dir / fname
        if not p.exists():
            logger.warning(f"File not found: {fname} — skipping")
            continue
        text = p.read_text(encoding="utf-8")
        file_id = get_field(text, "file_id")
        original_filename = get_field(text, "original_filename")
        status = get_field(text, "status")
        engine = get_field(text, "ocr_engine")
        if not file_id:
            logger.warning(f"No file_id in {fname} — skipping")
            continue
        targets.append({
            "md_path": p,
            "file_id": file_id,
            "original_filename": original_filename or p.stem + ".pdf",
            "status": status,
            "engine": engine,
        })
    return targets


def ocr_with_retry(pdf_bytes, file_id, filename, max_retries=3, per_page=False, page_delay=3.0):
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
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--delay", type=float, default=10.0)
    p.add_argument("--per-page", action="store_true")
    p.add_argument("--page-delay", type=float, default=15.0)
    p.add_argument("--files", nargs="+", help="Process only these filenames (stems or full names)")
    return p.parse_args()


def main():
    args = parse_args()
    md_dir = MD_BACKUP_DIR
    targets = collect_targets(md_dir)

    if args.files:
        filter_set = {f if f.endswith(".md") else f + ".md" for f in args.files}
        targets = [t for t in targets if t["md_path"].name in filter_set]

    logger.info(f"Found {len(targets)} target files")

    if args.limit > 0:
        targets = targets[: args.limit]

    if args.dry_run:
        for t in targets:
            flag = " [INACTIVE→active]" if t["status"] == "inactive" else ""
            flag += f" [already-Pro]" if t["engine"] == "gemini-2.5-pro" else ""
            print(f"  {t['md_path'].name}  [{t['file_id'][:20]}]{flag}")
        print(f"\nTotal: {len(targets)} (dry-run)")
        return

    success, failed = 0, []
    start_all = time.time()

    for i, t in enumerate(targets, 1):
        elapsed = (time.time() - start_all) / 60
        logger.info(f"[{i}/{len(targets)}] {t['md_path'].name}  (elapsed {elapsed:.1f}m)")
        if t["status"] == "inactive":
            logger.warning(f"  NOTE: was inactive — will be set active after re-OCR")

        try:
            pdf_bytes = stream_pdf(t["file_id"])
            logger.info(f"  PDF: {len(pdf_bytes)/1024:.0f} KB")
            t0 = time.time()
            result = ocr_with_retry(
                pdf_bytes, file_id=t["file_id"], filename=t["original_filename"],
                per_page=args.per_page, page_delay=args.page_delay,
            )
            logger.info(f"  OK: {result.get('doc_type','?')} | {len(result.get('text',''))} chars | {time.time()-t0:.0f}s")
            success += 1
        except Exception as e:
            logger.error(f"  FAIL: {e}")
            failed.append(t["md_path"].name)
            time.sleep(5)
            continue

        if i < len(targets) and args.delay > 0:
            time.sleep(args.delay)

    total_time = (time.time() - start_all) / 60
    print(f"\n{'='*60}")
    print(f"Done: {success} OK  |  {len(failed)} failed  |  {len(targets)} total")
    print(f"Total time: {total_time:.1f} min")
    if failed:
        print("\nFailed:")
        for f in failed:
            print(f"  - {f}")
    print("\nNext: force-reindex updated MDs then run eval.")


if __name__ == "__main__":
    main()
