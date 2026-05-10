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
from src.gemini_client import get_client

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


def generate_anchor(text: str) -> str:
    """Generate a retrieval anchor (บทสรุปสำหรับสืบค้น) from extracted markdown.

    Two-part generation to prevent cross-section hallucination:
    1. Keywords from full document
    2. Prose summary from ข้อวินิจฉัย sections only (fallback: full text)

    Returns empty string on failure (non-fatal — OCR result is still valid without anchor).
    """
    # Keywords use larger window (safe — just term extraction)
    kw_truncated = text[:8000]
    sum_truncated = text[:4000]
    try:
        client = _client()

        # Part 1: Keywords from full text (larger window)
        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=[_KEYWORDS_PROMPT.format(content=kw_truncated)],
        )
        keywords = response.text.strip()
        if not keywords:
            return ""

        # Part 2: Summary from ruling sections only, or fallback
        ruling_text = _extract_ruling_sections(text)
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

        if not summary:
            return keywords
        return f"{keywords}\n\n{summary}"

    except Exception as e:
        logger.warning(f"Anchor generation failed (non-fatal): {e}")
        return ""


def classify(pdf_bytes: bytes) -> dict:
    """Phase 1: Classify document type."""
    client = _client()
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
    client = _client()
    schema_fields = _SCHEMA.get(doc_type, _SCHEMA["default"]).strip()
    section_template = _SECTION_TEMPLATES.get(doc_type, _SECTION_TEMPLATES["default"]).strip()

    if per_page:
        # --- Per-page path: PDF → PNG (300 DPI) → Pro extract per page → Pro structure ---
        page_images = _pdf_pages_to_images(pdf_bytes)
        page_count = len(page_images)
        logger.info(f"  Per-page Pro extraction: {page_count} pages @ 300 DPI, delay={page_delay}s")

        raw_pages = []
        for i, png_bytes in enumerate(page_images, 1):
            logger.info(f"    Page {i}/{page_count} ({len(png_bytes)//1024} KB)")
            try:
                page_prompt = _EXTRACT_PAGE_RAW_PROMPT_TEMPLATE.format(
                    page_num=i, total_pages=page_count,
                )
                img_part = genai_types.Part.from_bytes(data=png_bytes, mime_type="image/png")
                resp = client.models.generate_content(
                    model=OCR_EXTRACT_MODEL,
                    contents=[page_prompt, img_part],
                )
                page_text = (resp.text or "").strip()
                if page_text and page_text != "---BLANK---":
                    raw_pages.append(f"<!-- Page {i} -->\n{page_text}")
            except Exception as e:
                logger.warning(f"    Page {i} extraction failed: {e} — inserting placeholder")
                raw_pages.append(f"<!-- Page {i} -->\n[หน้า {i}: extraction failed — {e}]")
            if i < page_count and page_delay > 0:
                time.sleep(page_delay)

        raw_text = "\n\n".join(raw_pages)
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
    else:
        # --- Original single-call path ---
        prompt = _EXTRACT_PROMPT_TEMPLATE.format(
            filename=filename,
            schema_fields=schema_fields,
            section_template=section_template,
            file_id=file_id,
        )
        part = _pdf_part(pdf_bytes)
        response = client.models.generate_content_stream(
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
