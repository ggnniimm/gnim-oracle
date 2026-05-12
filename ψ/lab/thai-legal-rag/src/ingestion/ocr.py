"""
Gemini Vision OCR — two-phase agentic approach.

Phase 1: Classify document type (Ruling_Committee, Ruling_Court, etc.)
Phase 2: Extract full content with type-specific YAML frontmatter schema

Uses Gemini File API (upload_file) — sends PDF directly to Gemini,
no page rendering needed. Much higher quality than image-based OCR.

Cache: SHA256(file_id) → JSON (skip re-OCR on repeat runs)
"""
import hashlib
import io
import json
import logging
import os
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import types as genai_types

from src.config import (
    GEMINI_FLASH_MODEL,
    OCR_EXTRACT_MODEL,
    MD_BACKUP_DIR,
    OCR_CACHE_DIR,
)
from src.gemini_client import get_client, get_ocr_client

logger = logging.getLogger(__name__)

# Document type → folder category mapping
DOC_TYPE_CATEGORY = {
    "Ruling_Committee": "ข้อหารือ กวจ.",
    "Ruling_Court": "คำพิพากษาศาลปกครอง",
    "Ruling_AttorneyGeneral": "ข้อหารืออัยการสูงสุด",
    "Circular": "หนังสือเวียน",
    "Contract": "สัญญา",
    "Unknown": "อื่นๆ",
}

# Type-specific frontmatter schema instructions for Gemini to fill
_SCHEMA = {
    "Ruling_Committee": """
doc_type: "ข้อหารือ"
issued_by: "กวจ."
date: "YYYY-MM-DD"  (วันที่จากหัวเอกสาร ใช้ปี ค.ศ. CE เท่านั้น เช่น 2023-07-27)
date_be: "YYYY-MM-DD"  (วันที่เดียวกัน แต่ปี พ.ศ. BE = CE+543 เช่น 2566-07-27)
doc_number: "เลขที่หนังสือเต็ม เช่น ที่ กค (กวจ) ๐๔๐๕.๒/๓๒๖๑๖"
title: "เรื่อง (subject line เต็ม verbatim จากเอกสาร)"
topic: "หมวดหมู่หลักของเนื้อหา เช่น ค่าปรับ | การตรวจรับงาน | การบอกเลิกสัญญา | ราคากลาง"
subtopic: "หมวดหมู่ย่อยที่เจาะจงกว่า topic"
laws_referenced: ["ชื่อกฎหมาย มาตรา/ข้อ เช่น พ.ร.บ.จัดซื้อจัดจ้างฯ พ.ศ. ๒๕๖๐ มาตรา ๖๐"]
quality: "good|review-needed|low"  (ประเมินคุณภาพ OCR ของตัวเอง)
quality_note: ""  (ถ้าไม่ใช่ good ให้ระบุสาเหตุ เช่น "หน้า 3 ภาพเบลอ")
""",
    "Ruling_Court": """
doc_type: "คำพิพากษา"
issued_by: "ศาลปกครอง"
date: "YYYY-MM-DD"  (ค.ศ. CE)
date_be: "YYYY-MM-DD"  (พ.ศ. BE = CE+543)
doc_number: "เลขคดี"
title: "ชื่อคดี (verbatim)"
topic: "หมวดหมู่หลักของเนื้อหา"
subtopic: "หมวดหมู่ย่อย"
court: "ชื่อศาล เช่น ศาลปกครองสูงสุด"

laws_referenced: ["กฎหมาย มาตรา/ข้อที่อ้างอิง"]
quality: "good|review-needed|low"
quality_note: ""
""",
    "Ruling_AttorneyGeneral": """
doc_type: "ข้อหารือ"
issued_by: "สำนักงานอัยการสูงสุด"
date: "YYYY-MM-DD"  (ค.ศ. CE)
date_be: "YYYY-MM-DD"  (พ.ศ. BE = CE+543)
doc_number: "เลขที่หนังสือ"
title: "เรื่อง (subject line เต็ม verbatim)"
topic: "หมวดหมู่หลักของเนื้อหา"
subtopic: "หมวดหมู่ย่อย"
laws_referenced: ["กฎหมาย มาตรา/ข้อที่อ้างอิง"]
quality: "good|review-needed|low"
quality_note: ""
""",
    "Circular": """
doc_type: "หนังสือเวียน"
issued_by: "กรมบัญชีกลาง"
date: "YYYY-MM-DD"  (ค.ศ. CE)
date_be: "YYYY-MM-DD"  (พ.ศ. BE = CE+543)
doc_number: "เลขที่ ว..."
title: "เรื่อง (subject line เต็ม verbatim)"
topic: "หมวดหมู่หลักของเนื้อหา"
subtopic: "หมวดหมู่ย่อย"
laws_referenced: ["กฎหมาย มาตรา/ข้อที่อ้างอิง"]
quality: "good|review-needed|low"
quality_note: ""
""",
    "default": """
doc_type: "อื่นๆ"
issued_by: ""
date: "YYYY-MM-DD"  (ค.ศ. CE)
date_be: "YYYY-MM-DD"  (พ.ศ. BE = CE+543)
doc_number: ""
title: "หัวข้อ/เรื่อง (verbatim)"
topic: "หมวดหมู่หลัก"
subtopic: ""
laws_referenced: []
quality: "good|review-needed|low"
quality_note: ""
""",
}

# Type-specific section templates. Different doc kinds need different
# Markdown body structure — circulars (หนังสือเวียน) don't have ประเด็นข้อหารือ,
# court judgments don't have ข้อวินิจฉัย-of-committee, etc.
_RULING_SECTIONS = """## ข้อเท็จจริง
[คัดลอกข้อความในส่วนข้อเท็จจริงออกมาทั้งหมด verbatim]

## ประเด็นข้อหารือ
[คัดลอกประเด็นคำถามที่หน่วยงานขอหารือออกมาทั้งหมด verbatim ทุกข้อ เช่น ๑. ... ๒. ... ๓. ...
ห้ามสรุปหรืออ้างอิงว่า "ตามที่กล่าวข้างต้น" ต้องคัดลอกข้อความจริงออกมาทั้งหมด]

## ข้อวินิจฉัย
[คัดลอกข้อวินิจฉัยของคณะกรรมการออกมาทั้งหมด verbatim ทุกข้อ]

## สรุปข้อวินิจฉัย
[สรุปเป็น bullet points ครบทุกประเด็นที่วินิจฉัย ไม่จำกัดจำนวน — ต้องมีทุกข้อหารือที่ปรากฏ]"""

_CIRCULAR_SECTIONS = """## หลักการและที่มา
[คัดลอก verbatim — ที่มา หลักการ อำนาจตามมาตรา/ข้อที่อ้างอิงในการออกหนังสือเวียน
รวมถึงระเบียบ/พ.ร.บ. ที่ถูกยกเว้นหรือผ่อนผัน ถ้ามี]

## แนวปฏิบัติ
[คัดลอกเนื้อหาแนวทางปฏิบัติทั้งหมด verbatim ทุกข้อ — รักษาเลขข้อเดิม (๑. ๒. ๓.๑ ๓.๒ ฯลฯ)
รวมตัวอย่างข้อความที่ให้แก้ไขในแบบประกาศ ถ้ามี]

## การใช้บังคับ
[คัดลอก verbatim — วันที่มีผลบังคับใช้ เงื่อนไขใช้กับกรณีใด การจัดซื้อจัดจ้างก่อน-หลังวันบังคับใช้
ถ้าไม่ระบุชัดเจน ใส่ "ไม่ระบุในเอกสาร"]

## ข้อสังเกต
[คัดลอก verbatim ถ้ามีหมายเหตุ ข้อยกเว้น หรือข้อสังเกตเพิ่มเติม
ถ้าไม่มี ใส่ "ไม่มี"]"""

_COURT_SECTIONS = """## ข้อเท็จจริง
[คัดลอกข้อเท็จจริงของคดี verbatim]

## ประเด็นวินิจฉัย
[คัดลอกประเด็นที่ศาลพิจารณา verbatim]

## คำวินิจฉัย
[คัดลอกคำวินิจฉัยของศาล verbatim ทุกประเด็น]

## สรุปคำวินิจฉัย
[สรุปเป็น bullet points ครบทุกประเด็น พร้อมหลักกฎหมายที่ใช้]"""

_SECTION_TEMPLATES = {
    "Ruling_Committee": _RULING_SECTIONS,
    "Ruling_AttorneyGeneral": _RULING_SECTIONS,
    "Ruling_Court": _COURT_SECTIONS,
    "Circular": _CIRCULAR_SECTIONS,
    "default": _RULING_SECTIONS,
}

_CLASSIFY_PROMPT = """
You are a legal document expert. Classify this Thai government document into ONE of these categories:

1. "Ruling_Committee" — ข้อหารือ กวจ. / คณะกรรมการวินิจฉัยปัญหาการจัดซื้อจัดจ้าง
   answering a specific case from a single agency. Has ## ข้อเท็จจริง about that
   agency's situation + ## ประเด็นข้อหารือ (questions asked) + ## ข้อวินิจฉัย (ruling).

2. "Ruling_Court" — คำพิพากษาศาลปกครอง / ศาลปกครองสูงสุด

3. "Ruling_AttorneyGeneral" — ข้อหารือสำนักงานอัยการสูงสุด

4. "Circular" — หนังสือเวียน issued TO ALL agencies (not a specific-case ruling).
   Strong signals — if ANY apply, this is "Circular":
   - Doc number contains "ว" (e.g. "ที่ กค (กวจ) ๐๔๐๕.๒/ว ๒๑๐" or "ว๖๔๕")
   - Subject starts with "แนวทางปฏิบัติ", "ซ้อมความเข้าใจ", "มาตรการ", "การยกเว้น",
     "การอนุมัติยกเว้น", "การผ่อนผัน", "หลักเกณฑ์"
   - Has "การใช้บังคับ" / "ให้มีผลใช้บังคับตั้งแต่..." section
   - Addresses "หัวหน้าหน่วยงานของรัฐทุกแห่ง" or no specific recipient
   - NO ## ข้อเท็จจริง of a specific case (general principle only)
   Note: กรมบัญชีกลาง / กวจ. / คณะกรรมการวินิจฉัยฯ also issue circulars
   — issuing body alone does NOT make it Ruling_Committee.

5. "Contract" — สัญญาจ้าง / สัญญาซื้อขาย

6. "Unknown" — ไม่แน่ใจ

Decision rule: if doc_number has "ว" → Circular. Issuer identity is secondary.

Return STRICT JSON only:
{"type": "CategoryName", "confidence": 0.0, "reasoning": "brief reason"}
"""

_EXTRACT_PROMPT_TEMPLATE = """
You are an expert OCR engine for Thai legal government documents.
Convert this PDF into Markdown with a YAML Frontmatter block.

**Output format — EXACTLY this structure:**

---
original_filename: {filename}
{schema_fields}
file_id: "{file_id}"
file_url: "https://drive.google.com/file/d/{file_id}/view"
---

# [title from document]

{section_template}

**Rules:**
- คัดลอกข้อความ verbatim ทุก section — ห้ามสรุป ห้ามตัด ห้ามอ้างอิงกลับ
- ใช้ section heading ตามที่กำหนดใน template ข้างต้น — ห้ามเปลี่ยนชื่อ ห้ามเพิ่ม/ลด section
- **ตารางทุกตารางในเอกสารต้องคงไว้ครบทุกตาราง** — แม้เนื้อหาในตารางจะดูซ้ำกับข้อความ
  ก่อนหน้า ก็ห้ามตัดทิ้ง ตารางคือส่วนของเอกสารต้นฉบับและต้องคัดลอก verbatim ทุก row/column
- **laws_referenced ต้องคงรายละเอียด วรรค/อนุมาตรา/(เลข) ตามที่ปรากฏในเอกสาร**
  ตัวอย่าง — ถ้าเอกสารระบุ "มาตรา ๒๙ วรรคหนึ่ง (๔)" ต้องเขียนครบทั้งสามส่วน
  ห้ามย่อเป็น "มาตรา ๒๙" เพียงอย่างเดียว
- **quality_note** เขียนเฉพาะปัญหา OCR ของตัวเอง (ภาพเบลอ ตัวอักษรไม่ชัด หน้าขาด ฯลฯ)
  ห้ามวิจารณ์เนื้อหาเอกสาร ห้าม flag เรื่องวันที่/ปี พ.ศ./ค.ศ. (ระบบจัดการให้แล้ว)
  ถ้า OCR สำเร็จไม่มีปัญหา ให้ใส่ `quality: "good"` และ `quality_note: ""`
- date ต้องใช้ปี ค.ศ. (CE) เสมอ เช่น 2023-07-27 ไม่ใช่ 2566-07-27
- date_be ใช้ปี พ.ศ. (BE = CE + 543) เช่น 2566-07-27
- Tables: ใช้ markdown table ปกติ — column separator ห้ามเกิน 4 dash ต่อ column
  (ห้าม `:----------------------...` ที่ยาวเกิน) ใช้ `| :--- |` หรือ `| --- |` พอ
- ห้ามใส่ `*`, `..`, dot-leader (`.....`), หรือ `___` แทน blank field ในเอกสาร —
  ปล่อยว่าง หรือใช้ `—` (em-dash) ถ้าจำเป็น
- ห้ามคัดลอก dot-leader ของหัวกระดาษ (`. . . . . . .`) ที่ใช้คั่นเลขข้อกับช่องว่าง
- Output raw Markdown only — NO code fences (no ```)
- YAML values with special chars must be quoted
- tags and laws_referenced must be YAML lists
"""


def _fix_frontmatter(text: str) -> str:
    """
    Gemini sometimes outputs YAML fields as list items inside frontmatter:
        - type: "value"
            - date: "value"
    This converts them to flat key: value pairs.
    """
    import re
    lines = text.splitlines()
    in_frontmatter = False
    result = []
    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            result.append(line)
            continue
        if in_frontmatter:
            # Case 1: "  - key: value" → "key: value"
            fixed = re.sub(r"^\s*-\s+(?=[a-zA-Z_]+:)", "", line)
            # Case 2: "  key: value" (indented but no dash) → "key: value"
            # Only strip indent from top-level scalar fields, not list items under them
            if fixed == line and re.match(r"^\s{2,}[a-zA-Z_]+:", line):
                fixed = line.lstrip()
            result.append(fixed)
        else:
            result.append(line)
    return "\n".join(result)


def _inject_frontmatter_fields(text: str, fields: dict) -> str:
    """Inject additional key: value fields before closing --- of frontmatter."""
    lines = text.splitlines()
    dash_count = 0
    insert_at = -1
    for i, line in enumerate(lines):
        if line.strip() == "---":
            dash_count += 1
            if dash_count == 2:
                insert_at = i
                break
    if insert_at == -1:
        return text

    new_lines = []
    for key, val in fields.items():
        if isinstance(val, str):
            new_lines.append(f'{key}: "{val}"')
        else:
            new_lines.append(f'{key}: {val}')

    return "\n".join(lines[:insert_at] + new_lines + lines[insert_at:])


_ARABIC_TO_THAI = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
_THAI_TO_ARABIC = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def _fix_date_from_filename(text: str, filename: str) -> str:
    """
    Cross-check date_be (and date) against the filename's date segment.

    Filename pattern: {prefix}_{กวจ}_{DOC_NUM}_{DATE_DDMMYY}_{TITLE}.pdf
    Date segment is immediately after doc_num: 6-digit string DDMMYY
      DD = day, MM = month, YY = last 2 digits of BE year (e.g. 68 → 2568 BE → 2025 CE)

    Example: 250468 → date_be: "2568-04-25", date: "2025-04-25"
    """
    import re

    stem = Path(filename).stem
    parts = stem.split("_")
    # Date segment is i+2 from the segment containing "กวจ"
    date_str = None
    for i, part in enumerate(parts):
        if "กวจ" in part and i + 2 < len(parts):
            candidate = parts[i + 2]
            if len(candidate) == 6 and candidate.isdigit():
                date_str = candidate
                break
    if not date_str:
        return text

    dd = date_str[0:2]
    mm = date_str[2:4]
    yy = date_str[4:6]
    be_year = f"25{yy}"
    ce_year = str(int(be_year) - 543)
    expected_date_be = f"{be_year}-{mm}-{dd}"
    expected_date = f"{ce_year}-{mm}-{dd}"

    def fix_date_be(m):
        current = m.group(1)
        if current != expected_date_be:
            logger.info(
                f"date_be mismatch: OCR={current!r} filename={expected_date_be!r} — correcting"
            )
            return f'date_be: "{expected_date_be}"'
        return m.group(0)

    def fix_date(m):
        current = m.group(1)
        if current != expected_date:
            logger.info(
                f"date mismatch: OCR={current!r} filename={expected_date!r} — correcting"
            )
            return f'date: "{expected_date}"'
        return m.group(0)

    text = re.sub(r'date_be:\s*"([^"]+)"', fix_date_be, text)
    text = re.sub(r'(?<![_\w])date:\s*"([^"]+)"', fix_date, text)
    return text


def _fix_doc_number_from_filename(text: str, filename: str) -> str:
    """
    Cross-check doc_number's trailing number against the filename.

    Filename pattern: {prefix}_{กวจ}_{DOC_NUM}_{DATE}_{TITLE}.pdf
    The second purely-numeric segment is the authoritative doc number.

    If OCR misread the handwritten number, replace it with the correct one.
    """
    import re

    stem = Path(filename).stem  # strip .pdf
    parts = stem.split("_")
    # Doc number is the purely-numeric segment immediately after the segment containing "กวจ"
    filename_num = None
    for i, part in enumerate(parts):
        if "กวจ" in part and i + 1 < len(parts):
            candidate = parts[i + 1]
            if candidate.isdigit():
                filename_num = candidate
                break
    if not filename_num:
        return text

    # Find doc_number: "..." in frontmatter and fix the part after the last /
    def fix_match(m):
        value = m.group(1)
        if "/" in value:
            prefix_part, num_part = value.rsplit("/", 1)
            # Convert Thai numerals → Arabic for comparison
            num_arabic = num_part.strip().translate(_THAI_TO_ARABIC)
            if num_arabic != filename_num:
                logger.info(
                    f"doc_number mismatch: OCR={num_arabic!r} filename={filename_num!r} — correcting"
                )
                thai_num = filename_num.translate(_ARABIC_TO_THAI)
                return f'doc_number: "{prefix_part}/{thai_num}"'
        return m.group(0)

    return re.sub(r'doc_number:\s*"([^"]+)"', fix_match, text)


def _get_page_count(pdf_bytes: bytes) -> int:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        return len(reader.pages)
    except Exception:
        return 0


def _pdf_pages_to_images(pdf_bytes: bytes, dpi: int = 300) -> list[bytes]:
    """Render each PDF page to PNG bytes at 300 DPI using pymupdf."""
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = dpi / 72  # pymupdf native resolution is 72 DPI
    mat = fitz.Matrix(zoom, zoom)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        images.append(pix.tobytes("png"))
    doc.close()
    return images



def _cache_path(file_id: str) -> Path:
    h = hashlib.sha256(file_id.encode()).hexdigest()[:16]
    return OCR_CACHE_DIR / f"{h}.json"


def _load_cache(file_id: str) -> dict | None:
    p = _cache_path(file_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _save_cache(file_id: str, data: dict) -> None:
    p = _cache_path(file_id)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_cache(file_id: str) -> bool:
    """
    Remove OCR cache for a specific file_id.

    Returns True if cache existed and was removed, False if it wasn't cached.
    Useful when you want to re-OCR a file (e.g. after re-uploading to Drive).
    """
    p = _cache_path(file_id)
    if p.exists():
        p.unlink()
        logger.info(f"Cleared OCR cache: {file_id} ({p.name})")
        return True
    logger.debug(f"No OCR cache found for: {file_id}")
    return False


def save_md_backup(filename: str, text: str) -> Path:
    """Save OCR output as human-readable .md file in md_backup/."""
    stem = Path(filename).stem
    out_path = MD_BACKUP_DIR / f"{stem}.md"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def _client() -> genai.Client:
    return get_client()


def _ocr_client() -> genai.Client:
    return get_ocr_client()


_PAGE_CALL_TIMEOUT = 300  # seconds — thread-level timeout per page (matches ocr_v4.py)


def _pdf_part(pdf_bytes: bytes):
    """Wrap PDF bytes as an inline Part — works on both Vertex and AI Studio.

    The previous File-API upload path is AI-Studio-only; Vertex rejects it with
    "This method is only supported in the Gemini Developer client." Inline data
    is supported on both backends up to ~20 MB per request.
    """
    return genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")


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

_RULING_SECTION_RE = re.compile(
    r"^##\s+(?:สรุป)?ข้อวินิจฉัย.*$", re.MULTILINE
)

_H2_HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

_LONG_DOC_ANCHOR_CHAR_THRESHOLD = 25_000


def _extract_ruling_sections(text: str) -> str:
    """Extract ข้อวินิจฉัย and สรุปข้อวินิจฉัย sections from markdown."""
    matches = list(_RULING_SECTION_RE.finditer(text))
    if not matches:
        return ""
    sections = []
    for match in matches:
        start = match.start()
        next_heading = re.search(r"^## ", text[match.end():], re.MULTILINE)
        end = match.end() + next_heading.start() if next_heading else len(text)
        section_text = text[start:end].strip()
        if section_text:
            sections.append(section_text)
    return "\n\n".join(sections)


def _sample_chapters_for_anchor(
    text: str,
    per_chapter_chars: int = 1500,
    max_total: int = 20_000,
) -> str:
    """Sample first N chars from every ## section so the anchor sees the whole doc.

    For long multi-chapter documents the default 8K window only covers the
    frontmatter + first chapter — keywords from later chapters (different form
    templates, later บท, ภาคผนวก, etc.) are lost. This helper concatenates
    the YAML frontmatter + a short head-of-section sample from each chapter,
    capped at max_total chars, so Flash sees one snippet per chapter.
    """
    fm_match = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    fm_block = fm_match.group(0) if fm_match else ""
    body = text[len(fm_block):]

    headings = list(_H2_HEADING_RE.finditer(body))
    if not headings:
        return (fm_block + body)[:max_total]

    parts: list[str] = [fm_block]
    for i, m in enumerate(headings):
        section_start = m.start()
        section_end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        section = body[section_start:section_end]
        # Keep the heading line + first per_chapter_chars of the section body
        parts.append(section[:per_chapter_chars])

    sampled = "\n\n".join(parts)
    return sampled[:max_total]


def generate_anchor(text: str) -> str:
    """Generate a retrieval anchor (บทสรุปสำหรับสืบค้น) from extracted markdown.

    Two-part generation to prevent cross-section hallucination:
    1. Keywords from full document (or per-chapter samples for long docs)
    2. Prose summary from ข้อวินิจฉัย sections only (fallback: cover-letter window)

    Returns empty string on failure (non-fatal — OCR result is still valid without anchor).
    """
    # Long docs: sample from every chapter so later sections (ภาคผนวก,
    # additional form templates, บทที่ ๒+) contribute keywords.
    # Short docs (≤25K chars): the 8K window already covers everything.
    if len(text) > _LONG_DOC_ANCHOR_CHAR_THRESHOLD:
        kw_truncated = _sample_chapters_for_anchor(text)
        logger.info(
            f"  Anchor: chapter-sampling mode "
            f"({len(_H2_HEADING_RE.findall(text))} sections, "
            f"sampled {len(kw_truncated):,}/{len(text):,} chars)"
        )
    else:
        kw_truncated = text[:8000]
    sum_truncated = text[:4000]
    client = _ocr_client()

    # Part 1: Keywords — required, returns empty anchor on failure.
    try:
        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=[_KEYWORDS_PROMPT.format(content=kw_truncated)],
        )
        keywords = response.text.strip()
    except Exception as e:
        logger.warning(f"Anchor keywords failed (non-fatal): {e}")
        return ""
    if not keywords:
        return ""

    # Part 2: Summary — best-effort, fall back to keywords-only on failure.
    # A summary timeout was previously discarding the keywords too.
    ruling_text = _extract_ruling_sections(text)
    try:
        if ruling_text:
            ruling_truncated = ruling_text[:3000]
            response = client.models.generate_content(
                model=GEMINI_FLASH_MODEL,
                contents=[_RULING_SUMMARY_PROMPT.format(content=ruling_truncated)],
            )
        else:
            response = client.models.generate_content(
                model=GEMINI_FLASH_MODEL,
                contents=[_FULLTEXT_SUMMARY_PROMPT.format(content=sum_truncated)],
            )
        summary = response.text.strip()
    except Exception as e:
        logger.warning(f"Anchor summary failed (keywords kept): {e}")
        return keywords

    if not summary:
        return keywords
    return f"{keywords}\n\n{summary}"


def classify(pdf_bytes: bytes) -> dict:
    """Phase 1: Classify document type."""
    client = _ocr_client()
    part = _pdf_part(pdf_bytes)
    try:
        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=[_CLASSIFY_PROMPT, part],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text)
        logger.debug(f"Classified: {result.get('type')} ({result.get('confidence', 0)*100:.0f}%)")
        return result
    except Exception as e:
        logger.warning(f"Classification failed: {e}")
        return {"type": "Unknown", "confidence": 0.0}


_TABLE_DASH_RE = re.compile(r"-{5,}")

_EXTRACT_PAGE_RAW_PROMPT_TEMPLATE = """\
คุณคือหุ่นยนต์ OCR ระดับสูง ถอดข้อความจากภาพหน้าเอกสารราชการไทยนี้แบบ 100% Verbatim

══ ข้อมูลหน้านี้ ══
นี่คือหน้าที่ {page_num} จากทั้งหมด {total_pages} หน้า

══ กฎเหล็ก ══
1. ถอดข้อความคำต่อคำ ห้ามสรุป ห้ามข้าม ห้ามแก้คำผิด แม้ต้นฉบับจะพิมพ์ผิด
2. รักษาเลขไทยตามต้นฉบับ ห้ามแปลงเป็นเลขอารบิก
3. รักษาโครงสร้าง: หัวกระดาษ (เลขที่ วันที่ เรื่อง) เนื้อหา ลำดับข้อ (๑. ๒. ๓.๑ ฯลฯ) ตาราง ลายเซ็น/ส่วนท้าย
4. ห้ามมีคำเกริ่นนำหรือคำอธิบายประกอบ
5. ถ้าหน้าว่างหรือมีแต่รูปภาพไม่มีข้อความ ให้ตอบ: ---BLANK---

══ ตัวเลขที่มักอ่านผิด (ระวังเป็นพิเศษ) ══
• ๒ (สอง) vs ๖ (หก)
• ๔ (สี่) vs ๕ (ห้า) vs ๙ (เก้า)
• ๘ (แปด) vs ๓ (สาม)
"""

_STRUCTURE_FROM_RAW_PROMPT_TEMPLATE = """
You are an expert OCR engine for Thai legal government documents.
Convert this extracted text (from {page_count} pages) into Markdown with a YAML Frontmatter block.

**Output format — EXACTLY this structure:**

---
original_filename: {filename}
{schema_fields}
file_id: "{file_id}"
file_url: "https://drive.google.com/file/d/{file_id}/view"
---

# [title from document]

{section_template}

**Rules:**
- คัดลอกข้อความ verbatim ทุก section — ห้ามสรุป ห้ามตัด ห้ามอ้างอิงกลับ
- ใช้ section heading ตามที่กำหนดใน template ข้างต้น — ห้ามเปลี่ยนชื่อ ห้ามเพิ่ม/ลด section
- **ตารางทุกตารางในเอกสารต้องคงไว้ครบทุกตาราง** — แม้เนื้อหาในตารางจะดูซ้ำกับข้อความ
  ก่อนหน้า ก็ห้ามตัดทิ้ง ตารางคือส่วนของเอกสารต้นฉบับและต้องคัดลอก verbatim ทุก row/column
- **laws_referenced ต้องคงรายละเอียด วรรค/อนุมาตรา/(เลข) ตามที่ปรากฏในเอกสาร**
  ตัวอย่าง — ถ้าเอกสารระบุ "มาตรา ๒๙ วรรคหนึ่ง (๔)" ต้องเขียนครบทั้งสามส่วน
  ห้ามย่อเป็น "มาตรา ๒๙" เพียงอย่างเดียว
- **quality_note** เขียนเฉพาะปัญหา OCR ของตัวเอง (ภาพเบลอ ตัวอักษรไม่ชัด หน้าขาด ฯลฯ)
  ห้ามวิจารณ์เนื้อหาเอกสาร ห้าม flag เรื่องวันที่/ปี พ.ศ./ค.ศ. (ระบบจัดการให้แล้ว)
  ถ้า OCR สำเร็จไม่มีปัญหา ให้ใส่ `quality: "good"` และ `quality_note: ""`
- date ต้องใช้ปี ค.ศ. (CE) เสมอ เช่น 2023-07-27 ไม่ใช่ 2566-07-27
- date_be ใช้ปี พ.ศ. (BE = CE + 543) เช่น 2566-07-27
- Tables: ใช้ markdown table ปกติ — column separator ห้ามเกิน 4 dash ต่อ column
  (ห้าม `:----------------------...` ที่ยาวเกิน) ใช้ `| :--- |` หรือ `| --- |` พอ
- ห้ามใส่ `*`, `..`, dot-leader (`.....`), หรือ `___` แทน blank field ในเอกสาร —
  ปล่อยว่าง หรือใช้ `—` (em-dash) ถ้าจำเป็น
- ห้ามคัดลอก dot-leader ของหัวกระดาษ (`. . . . . . .`) ที่ใช้คั่นเลขข้อกับช่องว่าง
- Output raw Markdown only — NO code fences (no ```)
- YAML values with special chars must be quoted
- tags and laws_referenced must be YAML lists

---

**ข้อความต้นฉบับ (คัดลอก verbatim, {page_count} หน้า):**

{raw_text}
"""


def _normalize_tables(text: str) -> str:
    """Collapse runaway dash padding in markdown table separators.

    Gemini sometimes outputs `| :--------------------- |` with hundreds of
    dashes per column, ballooning file size and breaking renderers. Compress
    any run of 5+ dashes back to 4. Preserves leading `:` for alignment.
    """
    return _TABLE_DASH_RE.sub("----", text)


LONG_DOC_PAGE_THRESHOLD = 10

_LONG_DOC_OUTLINE_PROMPT_TEMPLATE = """\
You are an expert structurer of Thai legal documents.

This is a long Thai government document ({total_pages} pages). The full raw OCR
text is provided below, with `<!-- Page N -->` markers separating pages. Read
it and produce a single JSON object with two keys:

1. "frontmatter": YAML field values for the document header.
2. "chapters": a list of major sections. Group consecutive pages that belong
   together. Use natural Thai chapter names — examples:
     "บทที่ ๑ บทนำและที่มา"
     "บทที่ ๒ แนวปฏิบัติ"
     "บทที่ ๓ การใช้บังคับ"
     "ภาคผนวก ก แบบประกาศประกวดราคา"
     "ภาคผนวก ข แบบสัญญาจ้าง"
   Each chapter must specify start_page and end_page (1-indexed, inclusive).
   All pages from 1 to {total_pages} MUST be covered exactly once — no gaps,
   no overlaps, chapters in page order, start_page <= end_page.

Return STRICT JSON only — no code fences, no commentary:

{{
  "frontmatter": {{
    "doc_type": {schema_doc_type_hint},
    "issued_by": "...",
    "date": "YYYY-MM-DD",
    "doc_number": "เลขที่หนังสือเต็ม เช่น ที่ กค (กวจ) ๐๔๐๕.๒/ว ๑๒๕",
    "title": "เรื่อง verbatim",
    "topic": "หมวดหมู่หลัก",
    "subtopic": "หมวดหมู่ย่อย",
    "laws_referenced": ["พ.ร.บ./ระเบียบ มาตรา/ข้อ/วรรค ที่อ้างอิง"],
    "quality": "good|review-needed|low",
    "quality_note": ""
  }},
  "chapters": [
    {{ "heading": "บทที่ ๑ ...", "start_page": 1, "end_page": N }}
  ]
}}

Rules:
- date in CE (e.g. 2023-03-01) — never พ.ศ. here
- laws_referenced must include มาตรา/ข้อ/วรรค where present in the doc
- Cover the full {total_pages} pages with no gaps, no overlaps
- Pages with only forms/templates should be grouped into a single ภาคผนวก chapter

---

ข้อความต้นฉบับ ({total_pages} หน้า):

{raw_text}
"""


_LONG_DOC_DOC_TYPE_HINT = {
    "Ruling_Committee": '"ข้อหารือ"',
    "Ruling_Court": '"คำพิพากษา"',
    "Ruling_AttorneyGeneral": '"ข้อหารือ"',
    "Circular": '"หนังสือเวียน"',
}


def _yaml_str(value) -> str:
    """Escape a value for inclusion in a YAML double-quoted scalar."""
    if value is None:
        return ""
    s = str(value)
    # Escape backslashes first, then double quotes
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _build_long_doc_yaml(fm: dict, file_id: str, filename: str) -> str:
    """Build YAML frontmatter block for long-doc mode from extracted fields."""
    date_ce = (fm.get("date") or "").strip()
    date_be = ""
    if len(date_ce) >= 4 and date_ce[:4].isdigit():
        try:
            date_be = f"{int(date_ce[:4]) + 543}{date_ce[4:]}"
        except ValueError:
            date_be = ""

    laws = fm.get("laws_referenced") or []
    if isinstance(laws, str):
        laws = [laws]
    laws_yaml = "[" + ", ".join(f'"{_yaml_str(l)}"' for l in laws) + "]"

    lines = [
        "---",
        f'original_filename: "{_yaml_str(filename)}"',
        f'doc_type: "{_yaml_str(fm.get("doc_type", ""))}"',
        f'issued_by: "{_yaml_str(fm.get("issued_by", ""))}"',
        f'date: "{_yaml_str(date_ce)}"',
        f'date_be: "{_yaml_str(date_be)}"',
        f'doc_number: "{_yaml_str(fm.get("doc_number", ""))}"',
        f'title: "{_yaml_str(fm.get("title", ""))}"',
        f'topic: "{_yaml_str(fm.get("topic", ""))}"',
        f'subtopic: "{_yaml_str(fm.get("subtopic", ""))}"',
        f"laws_referenced: {laws_yaml}",
        f'quality: "{_yaml_str(fm.get("quality", "good"))}"',
        f'quality_note: "{_yaml_str(fm.get("quality_note", ""))}"',
        f'file_id: "{_yaml_str(file_id)}"',
        f'file_url: "https://drive.google.com/file/d/{_yaml_str(file_id)}/view"',
        "---",
    ]
    return "\n".join(lines)


def _structure_long_doc(
    raw_pages: list[str],
    file_id: str,
    filename: str,
    doc_type: str,
    ocr_client,
) -> str:
    """Long-doc structure mode: one small Pro call for outline, body in Python.

    For documents >LONG_DOC_PAGE_THRESHOLD pages the verbatim 4-section template
    blows past per-minute token quota / read timeout. Instead, ask Pro for a
    chapter outline + frontmatter (small JSON output), then assemble the body
    from raw_pages slices keyed on page ranges. Body content is byte-identical
    to the raw extraction.
    """
    page_count = len(raw_pages)
    raw_text = "\n\n".join(raw_pages)

    # Same input truncation as the short-doc structure path
    _MAX_OUTLINE_INPUT_CHARS = 150_000
    if len(raw_text) > _MAX_OUTLINE_INPUT_CHARS:
        trimmed = raw_text[:_MAX_OUTLINE_INPUT_CHARS]
        marker = trimmed.rfind("\n\n<!-- Page ")
        if marker > 0:
            trimmed = trimmed[:marker]
        raw_text_for_outline = trimmed + "\n\n[... ส่วนที่เหลือถูกตัดสำหรับ outline ...]"
        logger.warning(
            f"  Long-doc outline input truncated: "
            f"{len(raw_text):,} → {len(raw_text_for_outline):,} chars"
        )
    else:
        raw_text_for_outline = raw_text

    prompt = _LONG_DOC_OUTLINE_PROMPT_TEMPLATE.format(
        total_pages=page_count,
        schema_doc_type_hint=_LONG_DOC_DOC_TYPE_HINT.get(doc_type, '"อื่นๆ"'),
        raw_text=raw_text_for_outline,
    )

    logger.info(f"  Long-doc mode: {page_count} pages — requesting outline (Pro)")
    # 600s timeout: outline processing 150K input chars can be slow when the
    # Pro pool is busy (observed up to 5+ min on us-central1).
    outline_client = get_ocr_client(timeout_ms=600_000)
    response = outline_client.models.generate_content(
        model=OCR_EXTRACT_MODEL,
        contents=[prompt],
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    outline = json.loads(response.text)
    fm = outline.get("frontmatter") or {}
    chapters = outline.get("chapters") or []
    if not chapters:
        raise RuntimeError("Long-doc outline returned empty chapters list")
    logger.info(f"  Outline: {len(chapters)} chapters")

    # Assemble body deterministically — body content is byte-identical
    # to the raw page extraction, just grouped under chapter headings.
    yaml_block = _build_long_doc_yaml(fm, file_id, filename)
    title = fm.get("title", "")
    parts = [yaml_block, "", f"# {title}", ""]
    used_pages: set[int] = set()
    for ch in chapters:
        heading = (ch.get("heading") or "").strip()
        try:
            start = int(ch.get("start_page", 1))
            end = int(ch.get("end_page", page_count))
        except (TypeError, ValueError):
            continue
        start = max(1, min(start, page_count))
        end = max(start, min(end, page_count))
        slice_pages = raw_pages[start - 1:end]
        used_pages.update(range(start, end + 1))
        parts.append(f"## {heading}")
        parts.append("")
        parts.append("\n\n".join(slice_pages))
        parts.append("")

    # Safety net: if the outline missed any pages, append them under ภาคผนวก เพิ่มเติม
    missing = sorted(set(range(1, page_count + 1)) - used_pages)
    if missing:
        logger.warning(f"  Long-doc outline missed pages: {missing} — appending")
        parts.append("## ภาคผนวก หน้าที่ไม่ได้จัดเข้าบท")
        parts.append("")
        for p in missing:
            parts.append(raw_pages[p - 1])
            parts.append("")

    return "\n".join(parts)


def extract(
    pdf_bytes: bytes,
    file_id: str,
    filename: str,
    doc_type: str,
    per_page: bool = False,
    page_delay: float = 15.0,
) -> str:
    """Phase 2: Extract full content with type-specific schema.

    per_page=True: Pro extracts raw text from each page individually, then
    Pro structures the combined raw text into the schema. Avoids streaming
    timeout on large PDFs at the cost of more Pro API calls.
    """
    client = _ocr_client()
    schema_fields = _SCHEMA.get(doc_type, _SCHEMA["default"]).strip()
    section_template = _SECTION_TEMPLATES.get(doc_type, _SECTION_TEMPLATES["default"]).strip()

    if per_page:
        # --- Per-page path: PDF → PNG (300 DPI) → Pro extract per page → Pro structure ---
        # Uses us-central1 quota pool (separate from global embedding pool).
        page_images = _pdf_pages_to_images(pdf_bytes)
        page_count = len(page_images)
        logger.info(f"  Per-page Pro extraction: {page_count} pages @ 300 DPI, delay={page_delay}s (us-central1)")

        # Intermediate save: persist raw pages so far to disk after each page.
        # On retry, load existing cache and resume from the first missing page.
        raw_cache = OCR_CACHE_DIR / f"{hashlib.sha256(file_id.encode()).hexdigest()[:16]}_raw.json"
        raw_pages = []
        start_page = 0  # 0-based index into page_images
        if raw_cache.exists():
            try:
                cached = json.loads(raw_cache.read_text(encoding="utf-8"))
                if isinstance(cached, list) and cached:
                    raw_pages = cached
                    start_page = len(cached)
                    if start_page >= page_count:
                        logger.info(f"  Raw cache complete ({page_count} pages) — skipping re-extraction")
                    else:
                        logger.info(f"  Resuming from page {start_page + 1}/{page_count} (cache had {start_page} pages)")
            except Exception:
                raw_pages = []
                start_page = 0

        ocr_client = _ocr_client()

        for i, png_bytes in enumerate(page_images[start_page:], start_page + 1):
            logger.info(f"    Page {i}/{page_count} ({len(png_bytes)//1024} KB)")
            page_prompt = _EXTRACT_PAGE_RAW_PROMPT_TEMPLATE.format(
                page_num=i, total_pages=page_count,
            )
            img_part = genai_types.Part.from_bytes(data=png_bytes, mime_type="image/png")

            try:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(
                        ocr_client.models.generate_content,
                        model=OCR_EXTRACT_MODEL,
                        contents=[page_prompt, img_part],
                    )
                    resp = future.result(timeout=_PAGE_CALL_TIMEOUT)
                page_text = (resp.text or "").strip()
                if page_text and page_text != "---BLANK---":
                    raw_pages.append(f"<!-- Page {i} -->\n{page_text}")
                    logger.info(f"    Page {i} ✓ {len(page_text):,} chars")
            except FutureTimeoutError:
                logger.warning(f"    Page {i} timed out after {_PAGE_CALL_TIMEOUT}s — placeholder")
                raw_pages.append(f"<!-- Page {i} -->\n[หน้า {i}: timeout]")
            except Exception as e:
                logger.warning(f"    Page {i} failed: {e} — placeholder")
                raw_pages.append(f"<!-- Page {i} -->\n[หน้า {i}: extraction failed — {e}]")

            # Persist progress after every page
            raw_cache.write_text(json.dumps(raw_pages, ensure_ascii=False), encoding="utf-8")

            if i < page_count and page_delay > 0:
                time.sleep(page_delay)

        raw_text = "\n\n".join(raw_pages)

        # Guard against token limit (65,536 input tokens on Vertex AI).
        # Thai text ≈ 2.4 chars/token; 150K chars ≈ 62K tokens, leaving headroom for template.
        _MAX_STRUCTURE_CHARS = 150_000
        if len(raw_text) > _MAX_STRUCTURE_CHARS:
            # Trim at the last complete page boundary within the limit.
            trimmed = raw_text[:_MAX_STRUCTURE_CHARS]
            last_page_marker = trimmed.rfind("\n\n<!-- Page ")
            if last_page_marker > 0:
                trimmed = trimmed[:last_page_marker]
            raw_text = trimmed + "\n\n[... ส่วนที่เหลือถูกตัด เกินขีดจำกัด input token ...]"
            logger.warning(
                f"  Raw text truncated: {len('\n\n'.join(raw_pages)):,} → {len(raw_text):,} chars "
                f"(page limit exceeded)"
            )

        if page_count > LONG_DOC_PAGE_THRESHOLD:
            # Long-doc path: small Pro call for outline only, body assembled
            # in Python from raw_pages. Avoids the streaming/timeout failure
            # mode of asking Pro to verbatim-copy 70+ pages in one call.
            text = _structure_long_doc(
                raw_pages=raw_pages,
                file_id=file_id,
                filename=filename,
                doc_type=doc_type,
                ocr_client=ocr_client,
            )
        else:
            prompt = _STRUCTURE_FROM_RAW_PROMPT_TEMPLATE.format(
                filename=filename,
                schema_fields=schema_fields,
                section_template=section_template,
                file_id=file_id,
                page_count=page_count,
                raw_text=raw_text,
            )
            response = client.models.generate_content_stream(
                model=OCR_EXTRACT_MODEL,
                contents=[prompt],
                config=genai_types.GenerateContentConfig(),
            )
            text = ""
            for chunk in response:
                if chunk.text:
                    text += chunk.text
    else:
        # --- Original single-call path (also uses us-central1) ---
        prompt = _EXTRACT_PROMPT_TEMPLATE.format(
            filename=filename,
            schema_fields=schema_fields,
            section_template=section_template,
            file_id=file_id,
        )
        part = _pdf_part(pdf_bytes)
        ocr_client = _ocr_client()
        response = ocr_client.models.generate_content_stream(
            model=OCR_EXTRACT_MODEL,
            contents=[prompt, part],
            config=genai_types.GenerateContentConfig(),
        )
        text = ""
        for chunk in response:
            if chunk.text:
                text += chunk.text

    # Strip code fences if Gemini added them
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].startswith("```") else lines
        text = "\n".join(lines).strip()

    # Fix frontmatter indentation issues
    text = _fix_frontmatter(text)

    # Collapse runaway dash padding in table separators (Gemini OCR artifact)
    text = _normalize_tables(text)

    return text


def pdf_to_markdown(
    pdf_bytes: bytes,
    file_id: str,
    filename: str = "document.pdf",
    force: bool = False,
    per_page: bool = False,
    page_delay: float = 15.0,
) -> dict:
    """
    Main OCR entry point. Two-phase: classify → extract.

    Returns:
        {
            "text": str,          # Full markdown with YAML frontmatter
            "doc_type": str,      # e.g. "Ruling_Committee"
            "category": str,      # Thai category name
            "confidence": float,
        }
    """
    if not force:
        cached = _load_cache(file_id)
        if cached is not None:
            logger.debug(f"OCR cache hit: {file_id}")
            return cached

    # Phase 1: Classify
    classification = classify(pdf_bytes)
    doc_type = classification.get("type", "Unknown")
    confidence = classification.get("confidence", 0.0)
    logger.info(f"Classified '{filename}' → {doc_type} ({confidence*100:.0f}%)")

    # Filename safety net: any file whose doc-number segment starts with "ว" is a
    # circular, regardless of issuer. The classifier sometimes mis-routes these
    # to Ruling_Committee because กวจ./กรมบัญชีกลาง issues both rulings AND circulars.
    if doc_type != "Circular" and re.search(r"[-_]ว\d", filename):
        logger.info(
            f"Filename override: '{filename}' has ว-prefix doc number → Circular "
            f"(was {doc_type})"
        )
        doc_type = "Circular"

    # Phase 2: Extract
    text = extract(
        pdf_bytes, file_id=file_id, filename=filename, doc_type=doc_type,
        per_page=per_page, page_delay=page_delay,
    )

    # Cross-check doc_number against filename (filename is authoritative for the numeric part)
    text = _fix_doc_number_from_filename(text, filename)

    # Cross-check date against filename's DDMMYY segment (filename is authoritative)
    text = _fix_date_from_filename(text, filename)

    # Inject pipeline-generated fields into frontmatter
    ocr_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    page_count = _get_page_count(pdf_bytes)
    text = _inject_frontmatter_fields(text, {
        "page_count": page_count,
        "ocr_engine": OCR_EXTRACT_MODEL,
        "ocr_date": ocr_date,
        "status": "active",
        "status_note": "unverified",
    })

    # Generate retrieval anchor
    anchor = generate_anchor(text)
    if anchor:
        text += f"\n\n## บทสรุปสำหรับสืบค้น\n\n{anchor}"
        logger.info(f"Generated retrieval anchor for '{filename}'")

    result = {
        "text": text,
        "doc_type": doc_type,
        "category": DOC_TYPE_CATEGORY.get(doc_type, "อื่นๆ"),
        "confidence": confidence,
        "file_id": file_id,
        "filename": filename,
    }

    _save_cache(file_id, result)

    # Save human-readable MD backup
    md_path = save_md_backup(filename, text)
    logger.debug(f"MD backup saved: {md_path}")

    return result
