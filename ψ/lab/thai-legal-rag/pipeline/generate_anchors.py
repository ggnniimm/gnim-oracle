"""
Batch-generate retrieval anchors (บทสรุปสำหรับสืบค้น) for MD files.

Reads existing MD files from md_backup/, sends content to Gemini to generate
a keyword-dense retrieval summary, and appends it as ## บทสรุปสำหรับสืบค้น.

Usage:
  THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/generate_anchors.py
  THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/generate_anchors.py --file "specific_file.md"
  THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/generate_anchors.py --dry-run
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google import genai

from src.config import GEMINI_API_KEYS, GEMINI_FLASH_MODEL, MD_BACKUP_DIR

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

ANCHOR_HEADING = "## บทสรุปสำหรับสืบค้น"

_ANCHOR_PROMPT = """\
จากเอกสารกฎหมายไทยต่อไปนี้ ให้สร้างบทสรุปสำหรับสืบค้น (retrieval summary) ดังนี้:

บรรทัดที่ 1-2: คำสำคัญ 15-20 คำ คั่นด้วยช่องว่าง (เช่น ชื่อเรื่อง เลขที่หนังสือ มาตรา ข้อกฎหมาย หลักการสำคัญ)
บรรทัดที่ 3-5: สรุปหลักการหรือข้อวินิจฉัยสำคัญ 2-3 ประโยค ใช้ภาษาที่เหมาะสำหรับการค้นหา

ห้ามใส่หัวข้อ ห้ามใส่ bullet ให้เขียนเป็น plain text เท่านั้น

---
{content}
"""

_KEY_INDEX = 0


def _get_key() -> str:
    global _KEY_INDEX
    if not GEMINI_API_KEYS:
        raise ValueError("No GEMINI_API_KEYS configured. Set GEMINI_API_KEY env var.")
    key = GEMINI_API_KEYS[_KEY_INDEX % len(GEMINI_API_KEYS)]
    _KEY_INDEX += 1
    return key


def _client() -> genai.Client:
    return genai.Client(api_key=_get_key())


def has_anchor(text: str) -> bool:
    """Check if file already contains an anchor section."""
    return ANCHOR_HEADING in text


def generate_anchor(text: str, client: genai.Client | None = None) -> str:
    """Generate a retrieval anchor from markdown text using Gemini.

    Args:
        text: Full markdown content of the document.
        client: Optional Gemini client (creates one if not provided).

    Returns:
        The anchor text (without the heading), or empty string on failure.
    """
    if client is None:
        client = _client()

    # Truncate to ~4000 chars to avoid token waste
    truncated = text[:4000]

    prompt = _ANCHOR_PROMPT.format(content=truncated)

    try:
        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=[prompt],
        )
        anchor = response.text.strip()
        return anchor
    except Exception as e:
        logger.error(f"Gemini anchor generation failed: {e}")
        return ""


def append_anchor(file_path, anchor_text: str) -> None:
    """Append anchor section to an MD file."""
    current = file_path.read_text(encoding="utf-8")
    current = current.rstrip()
    current += f"\n\n{ANCHOR_HEADING}\n\n{anchor_text}\n"
    file_path.write_text(current, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate retrieval anchors for MD files")
    parser.add_argument("--file", type=str, help="Process a single file (name only, not full path)")
    parser.add_argument("--dry-run", action="store_true", help="Print anchors without writing")
    args = parser.parse_args()

    # Collect files to process
    if args.file:
        target = MD_BACKUP_DIR / args.file
        if not target.exists():
            logger.error(f"File not found: {target}")
            sys.exit(1)
        md_files = [target]
    else:
        md_files = sorted(MD_BACKUP_DIR.glob("*.md"))

    if not md_files:
        logger.info("No MD files found.")
        return

    # Filter out files that already have anchors
    to_process = []
    for f in md_files:
        content = f.read_text(encoding="utf-8")
        if has_anchor(content):
            logger.debug(f"Skipping (already has anchor): {f.name}")
        else:
            to_process.append(f)

    total = len(to_process)
    skipped = len(md_files) - total
    if skipped:
        logger.info(f"Skipping {skipped} files that already have anchors")

    if total == 0:
        logger.info("All files already have anchors. Nothing to do.")
        return

    logger.info(f"Generating anchors for {total} files...")

    client = _client()
    success = 0
    failed = 0

    for i, file_path in enumerate(to_process, 1):
        content = file_path.read_text(encoding="utf-8")
        anchor = generate_anchor(content, client=client)

        if not anchor:
            logger.warning(f"[{i}/{total}] FAILED: {file_path.name}")
            failed += 1
            continue

        if args.dry_run:
            print(f"\n{'='*60}")
            print(f"[{i}/{total}] {file_path.name}")
            print(f"{'='*60}")
            print(anchor)
        else:
            append_anchor(file_path, anchor)
            logger.info(f"[{i}/{total}] Generated anchor for {file_path.name}")

        success += 1

        # Rate limiting: ~1 req/sec
        if i < total:
            time.sleep(1.0)

    logger.info(f"Done. Success: {success}, Failed: {failed}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
