"""
Fix truncated OCR files: targeted re-extraction of ข้อวินิจฉัย + สรุปข้อวินิจฉัย.

For each flagged file (has file_id):
1. Download PDF from Drive
2. Ask Gemini to extract complete ข้อวินิจฉัย + สรุปข้อวินิจฉัย verbatim
3. Patch MD file (replace the two sections)
4. Log result

Run from thai-legal-rag/ directory with:
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/fix_truncated_ocr.py
"""
from __future__ import annotations
import re
import sys
import time
import yaml
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True, raise_error_if_not_found=False))

from src.ingestion.drive import stream_pdf
from src.ingestion.ocr import _upload_pdf, _client, _cleanup
from google.genai import types as genai_types

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/fix_truncated.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

MD_DIR = Path("data/md_backup")

# Files flagged by audit (by prefix — will glob for full name)
FLAGGED_PREFIXES = [
    "001_กวจ_26242_270766",
    "001กวจ_13902_110466",
    "002_กวจ_44027_111165",
    "02_กวจ_33886_090864",
    "กค(หวจ)0405.2_050764",
    "กค+(กวจ)+0405.2-039278",
    "ตอบข้อหารือ+นย.ทม.พังงา+59137",
    "๒๘",
    "๖๓",
    "03_กวจ_38712_060964",
    "01_กวจ_36000_030968",
    "02_กวจ_30690_120764",
    "02_กวจ_57273_131264",
    "03_กวจ_46035_111064",
    "๒๖",
    "01_กวจ_57077_131264",
    "02_กวจ_43981_300964",
    "001_กวจ_24499_170766",
    "02_กวจ_40750_160964",
    "001กวจ_38872_241066",
    "01_กวจ_21382_110564",
    "01_กวจ_40547_300968",
    "001_กวจ_4646_040268",
    "001_กวจ_10868_220365",
    "001_กวจ_13680_100466",
    "กวจ_0405.4_22315_170564",
    "03_กวจ_54811_261164",
]

_EXTRACT_PROMPT = """
You are an expert in Thai government procurement law documents.

This document is a ข้อหารือ (legal inquiry response) from กวจ. (คณะกรรมการวินิจฉัยปัญหาการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ).

Please extract VERBATIM (word for word, do NOT summarize or paraphrase) the following two sections:

1. The COMPLETE ข้อวินิจฉัย section — ALL numbered items (๑. ๒. ๓. etc.) with their full text
2. The COMPLETE สรุปข้อวินิจฉัย section — all bullet points

Output format (use these exact section headers):

## ข้อวินิจฉัย
[verbatim text of all ข้อวินิจฉัย items — every numbered item, no truncation]

## สรุปข้อวินิจฉัย
[verbatim or accurate bullet point summary]

Rules:
- DO NOT truncate or omit any numbered item (๑. ๒. ๓. ...)
- DO NOT summarize — copy verbatim
- Output raw Thai text only — no code fences, no markdown formatting beyond the ## headers
- If a numbered item cites law text, include the full quoted text
"""


def parse_fm(text: str) -> tuple[dict, str, str]:
    """Returns (meta, frontmatter_raw, body)."""
    m = re.match(r'^(---\s*\n)(.*?)\n(---\s*\n)', text, re.DOTALL)
    if m:
        fm_raw = m.group(1) + m.group(2) + "\n" + m.group(3)
        body = text[m.end():]
        try:
            meta = yaml.safe_load(m.group(2)) or {}
        except Exception:
            meta = {}
        return meta, fm_raw, body
    return {}, "", text


def patch_sections(original_body: str, new_vinij_and_surup: str) -> str:
    """
    Replace ข้อวินิจฉัย + สรุปข้อวินิจฉัย sections with extracted content.
    Preserves everything before ข้อวินิจฉัย.
    """
    # Find start of ## ข้อวินิจฉัย
    m = re.search(r'\n## ข้อวินิจฉัย', original_body)
    if not m:
        # No section found — append at end
        return original_body.rstrip() + "\n\n" + new_vinij_and_surup.strip() + "\n"

    before = original_body[:m.start()]
    return before.rstrip() + "\n\n" + new_vinij_and_surup.strip() + "\n"


def extract_sections(response_text: str) -> str:
    """Extract ## ข้อวินิจฉัย ... ## สรุปข้อวินิจฉัย ... from Gemini response."""
    text = response_text.strip()
    # Strip code fences
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].startswith("```") else lines
        text = "\n".join(lines).strip()
    # Must contain ข้อวินิจฉัย
    if "ข้อวินิจฉัย" not in text:
        return ""
    # Ensure it starts from ## ข้อวินิจฉัย
    m = re.search(r'##\s*ข้อวินิจฉัย', text)
    if m:
        text = text[m.start():]
    return text


def fix_file(md_path: Path) -> str:
    """
    Fix one MD file. Returns status string.
    """
    text = md_path.read_text(encoding="utf-8")
    meta, fm_raw, body = parse_fm(text)

    file_id = meta.get("file_id", "")
    if not file_id:
        return "SKIP (no file_id)"

    # Download PDF
    try:
        pdf_bytes = stream_pdf(file_id)
    except Exception as e:
        return f"FAIL download: {e}"

    # Call Gemini
    try:
        client = _client()
        uploaded = _upload_pdf(client, pdf_bytes, md_path.name)
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[_EXTRACT_PROMPT, uploaded],
                config=genai_types.GenerateContentConfig(max_output_tokens=8192),
            )
            raw = response.text or ""
        finally:
            _cleanup(client, uploaded)
    except Exception as e:
        return f"FAIL gemini: {e}"

    new_sections = extract_sections(raw)
    if not new_sections or len(new_sections) < 100:
        return f"FAIL parse (got {len(raw)} chars, extracted {len(new_sections)} chars)"

    # Patch the body
    new_body = patch_sections(body, new_sections)
    md_path.write_text(fm_raw + new_body, encoding="utf-8")

    return f"OK ({len(raw)} chars extracted)"


def main():
    # Resolve full paths from prefixes
    files_to_fix: list[Path] = []
    for prefix in FLAGGED_PREFIXES:
        matches = sorted(MD_DIR.glob(f"{prefix}*.md"))
        if not matches:
            matches = [p for p in MD_DIR.iterdir()
                       if p.suffix == ".md" and p.name.startswith(prefix[:20])]
        if matches:
            files_to_fix.append(matches[0])
        else:
            logger.warning(f"Not found: {prefix}")

    logger.info(f"Fixing {len(files_to_fix)} files...")

    results = {"OK": [], "SKIP": [], "FAIL": []}
    for i, md_path in enumerate(files_to_fix, 1):
        logger.info(f"[{i}/{len(files_to_fix)}] {md_path.name[:60]}")
        status = fix_file(md_path)
        logger.info(f"  → {status}")

        if status.startswith("OK"):
            results["OK"].append(md_path.name)
        elif status.startswith("SKIP"):
            results["SKIP"].append(md_path.name)
        else:
            results["FAIL"].append((md_path.name, status))

        # Rate limit: 1 req/sec to avoid hammering Gemini
        if i < len(files_to_fix):
            time.sleep(2)

    logger.info("\n=== DONE ===")
    logger.info(f"OK:   {len(results['OK'])}")
    logger.info(f"SKIP: {len(results['SKIP'])}")
    logger.info(f"FAIL: {len(results['FAIL'])}")
    for fname, err in results["FAIL"]:
        logger.info(f"  FAIL {fname[:50]}: {err}")

    return results


if __name__ == "__main__":
    main()
