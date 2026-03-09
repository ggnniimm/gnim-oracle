"""
Batch-generate retrieval anchors (บทสรุปสำหรับสืบค้น) for MD files.

Reads existing MD files from md_backup/, sends content to Gemini to generate
a keyword-dense retrieval summary, and appends it as ## บทสรุปสำหรับสืบค้น.

v2: Section-restricted generation — keywords from full text, prose summary
from ข้อวินิจฉัย/สรุปข้อวินิจฉัย sections only (prevents cross-section
contamination that caused 36% hallucination rate).

Usage:
  THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/generate_anchors.py
  THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/generate_anchors.py --file "specific_file.md"
  THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/generate_anchors.py --dry-run
  THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/generate_anchors.py --force  # regenerate existing
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import GEMINI_FLASH_MODEL, MD_BACKUP_DIR
from src.gemini_client import get_client

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

ANCHOR_HEADING = "## บทสรุปสำหรับสืบค้น"

# --- Prompts ---

_KEYWORDS_PROMPT = """\
จากเอกสารกฎหมายไทยต่อไปนี้ ให้สร้างรายการคำสำคัญ 25-30 คำ คั่นด้วยช่องว่าง
ครอบคลุมทั้ง:
- ชื่อเรื่อง เลขที่หนังสือ มาตรา ข้อกฎหมาย
- หลักการสำคัญ ข้อวินิจฉัย
- คำปฏิบัติ/ขั้นตอน เช่น ตรวจรับ ลงนาม แก้ไขสัญญา เนื้องาน ผลิตภายในประเทศ บอกเลิกสัญญา ฯลฯ

กฎเคร่งครัด:
- ใช้เฉพาะคำที่ปรากฏในเอกสาร
- ห้ามใส่หัวข้อ ห้ามใส่ bullet ให้เขียนเป็น plain text บรรทัดเดียว

---
{content}
"""

_RULING_SUMMARY_PROMPT = """\
จากข้อวินิจฉัยต่อไปนี้ ให้สรุปหลักการหรือข้อวินิจฉัยสำคัญ 2-3 ประโยค

กฎเคร่งครัด:
- สรุปเฉพาะสิ่งที่ปรากฏในข้อวินิจฉัยนี้เท่านั้น
- ห้ามเพิ่มข้อมูลจากส่วนอื่นของเอกสาร
- ห้ามตีความหรือขยายความเกินจากข้อวินิจฉัย
- ห้ามใส่หัวข้อ ห้ามใส่ bullet ให้เขียนเป็น plain text

---
{content}
"""

# Fallback: used when no ruling sections exist (e.g. หนังสือเวียน, ระเบียบ)
_FULLTEXT_SUMMARY_PROMPT = """\
จากเอกสารกฎหมายไทยต่อไปนี้ ให้สรุปหลักการหรือสาระสำคัญ 2-3 ประโยค

กฎเคร่งครัด:
- ใช้เฉพาะข้อมูลที่ปรากฏในเอกสาร
- ห้ามเพิ่มตัวอย่างที่ไม่มีในเอกสาร ห้ามใส่คำว่า "เช่น" ตามด้วยสิ่งที่คิดเอง
- ห้ามตีความหรือขยายความเกินจากเนื้อหาเอกสาร
- ห้ามใส่หัวข้อ ห้ามใส่ bullet ให้เขียนเป็น plain text

---
{content}
"""

# Matches ## ข้อวินิจฉัย or ## สรุปข้อวินิจฉัย (with optional trailing text)
_RULING_SECTION_RE = re.compile(
    r"^##\s+(?:สรุป)?ข้อวินิจฉัย.*$", re.MULTILINE
)


def extract_ruling_sections(text: str) -> str:
    """Extract ข้อวินิจฉัย and สรุปข้อวินิจฉัย sections from markdown.

    Returns concatenated ruling text, or empty string if no sections found.
    """
    matches = list(_RULING_SECTION_RE.finditer(text))
    if not matches:
        return ""

    sections = []
    for match in matches:
        start = match.start()
        # Find next ## heading after this one (or end of text)
        next_heading = re.search(r"^## ", text[match.end():], re.MULTILINE)
        if next_heading:
            end = match.end() + next_heading.start()
        else:
            end = len(text)
        section_text = text[start:end].strip()
        if section_text:
            sections.append(section_text)

    return "\n\n".join(sections)


def has_anchor(text: str) -> bool:
    """Check if file already contains an anchor section."""
    return ANCHOR_HEADING in text


def strip_anchor(text: str) -> str:
    """Remove existing anchor section from text."""
    idx = text.find(ANCHOR_HEADING)
    if idx == -1:
        return text
    return text[:idx].rstrip()


def _call_gemini(client, prompt: str) -> str:
    """Single Gemini call, returns stripped text or empty string."""
    response = client.models.generate_content(
        model=GEMINI_FLASH_MODEL,
        contents=[prompt],
    )
    return response.text.strip()


def generate_anchor(text: str, client=None) -> str:
    """Generate a retrieval anchor from markdown text using Gemini.

    Two-part generation:
    1. Keywords from full document (safe — just extracting terms)
    2. Prose summary from ข้อวินิจฉัย sections only (prevents hallucination)
       Falls back to full-text summary if no ruling sections exist.

    Args:
        text: Full markdown content of the document.
        client: Optional Gemini client (creates one if not provided).

    Returns:
        The anchor text (without the heading), or empty string on failure.
    """
    if client is None:
        client = get_client()

    # Strip existing anchor if present (for regeneration)
    text = strip_anchor(text)
    # Keywords use larger window (safe — just term extraction, no hallucination risk)
    kw_truncated = text[:8000]
    # Summary uses smaller window
    sum_truncated = text[:4000]

    try:
        # Part 1: Keywords from full text (larger window)
        keywords = _call_gemini(client, _KEYWORDS_PROMPT.format(content=kw_truncated))
        if not keywords:
            return ""

        # Part 2: Summary from ruling sections only, or fallback to full text
        ruling_text = extract_ruling_sections(text)
        if ruling_text:
            ruling_truncated = ruling_text[:3000]
            summary = _call_gemini(
                client, _RULING_SUMMARY_PROMPT.format(content=ruling_truncated)
            )
            logger.debug("Using ruling-restricted summary")
        else:
            summary = _call_gemini(
                client, _FULLTEXT_SUMMARY_PROMPT.format(content=sum_truncated)
            )
            logger.debug("No ruling sections found, using full-text summary")

        if not summary:
            return keywords  # keywords alone still useful

        return f"{keywords}\n\n{summary}"

    except Exception as e:
        logger.error(f"Gemini anchor generation failed: {e}")
        return ""


def replace_anchor(file_path, anchor_text: str) -> None:
    """Replace or append anchor section in an MD file."""
    current = file_path.read_text(encoding="utf-8")
    current = strip_anchor(current).rstrip()
    current += f"\n\n{ANCHOR_HEADING}\n\n{anchor_text}\n"
    file_path.write_text(current, encoding="utf-8")


def append_anchor(file_path, anchor_text: str) -> None:
    """Append anchor section to an MD file (legacy compat)."""
    replace_anchor(file_path, anchor_text)


def main():
    parser = argparse.ArgumentParser(description="Generate retrieval anchors for MD files")
    parser.add_argument("--file", type=str, help="Process a single file (name only, not full path)")
    parser.add_argument("--dry-run", action="store_true", help="Print anchors without writing")
    parser.add_argument("--force", action="store_true", help="Regenerate anchors even if they exist")
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

    # Filter out files that already have anchors (unless --force)
    to_process = []
    for f in md_files:
        content = f.read_text(encoding="utf-8")
        if has_anchor(content) and not args.force:
            logger.debug(f"Skipping (already has anchor): {f.name}")
        else:
            to_process.append(f)

    total = len(to_process)
    skipped = len(md_files) - total
    if skipped:
        logger.info(f"Skipping {skipped} files that already have anchors (use --force to regenerate)")

    if total == 0:
        logger.info("All files already have anchors. Nothing to do.")
        return

    logger.info(f"Generating anchors for {total} files...")

    client = get_client()
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
            ruling = extract_ruling_sections(strip_anchor(content))
            mode = "RULING-RESTRICTED" if ruling else "FULL-TEXT"
            print(f"\n{'='*60}")
            print(f"[{i}/{total}] {file_path.name} ({mode})")
            print(f"{'='*60}")
            print(anchor)
        else:
            replace_anchor(file_path, anchor)
            logger.info(f"[{i}/{total}] Generated anchor for {file_path.name}")

        success += 1

        # Rate limiting: ~1.5 req/sec (2 Gemini calls per file now)
        if i < total:
            time.sleep(1.5)

    logger.info(f"Done. Success: {success}, Failed: {failed}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
