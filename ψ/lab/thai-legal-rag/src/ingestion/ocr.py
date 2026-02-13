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
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import types as genai_types

from src.config import (
    GEMINI_API_KEYS,
    GEMINI_FLASH_MODEL,
    MD_BACKUP_DIR,
    OCR_CACHE_DIR,
)

logger = logging.getLogger(__name__)

_KEY_INDEX = 0

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

_CLASSIFY_PROMPT = """
You are a legal document expert. Classify this Thai government document into ONE of these categories:

1. "Ruling_Committee" — ข้อหารือ กวจ. / กรมบัญชีกลาง / คณะกรรมการวินิจฉัยปัญหาการจัดซื้อจัดจ้าง
2. "Ruling_Court" — คำพิพากษาศาลปกครอง / ศาลปกครองสูงสุด
3. "Ruling_AttorneyGeneral" — ข้อหารือสำนักงานอัยการสูงสุด
4. "Circular" — หนังสือเวียน / ว...
5. "Contract" — สัญญาจ้าง / สัญญาซื้อขาย
6. "Unknown" — ไม่แน่ใจ

Analyze the header, logos, reference number format, and subject line.

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

## ข้อเท็จจริง
[คัดลอกข้อความในส่วนข้อเท็จจริงออกมาทั้งหมด verbatim]

## ประเด็นข้อหารือ
[คัดลอกประเด็นคำถามที่หน่วยงานขอหารือออกมาทั้งหมด verbatim ทุกข้อ เช่น ๑. ... ๒. ... ๓. ...
ห้ามสรุปหรืออ้างอิงว่า "ตามที่กล่าวข้างต้น" ต้องคัดลอกข้อความจริงออกมาทั้งหมด]

## ข้อวินิจฉัย
[คัดลอกข้อวินิจฉัยของคณะกรรมการออกมาทั้งหมด verbatim ทุกข้อ]

## สรุปข้อวินิจฉัย
[สรุปเป็น bullet points ไม่เกิน 5 ข้อ]

**Rules:**
- คัดลอกข้อความ verbatim ทุก section — ห้ามสรุป ห้ามตัด ห้ามอ้างอิงกลับ
- ส่วน ประเด็นข้อหารือ ต้องมีทุกประเด็นที่ปรากฏในเอกสาร (๑. ๒. ๓. ...)
- date ต้องใช้ปี ค.ศ. (CE) เสมอ เช่น 2023-07-27 ไม่ใช่ 2566-07-27
- date_be ใช้ปี พ.ศ. (BE = CE + 543) เช่น 2566-07-27
- Preserve tables as markdown tables
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


def _get_key() -> str:
    global _KEY_INDEX
    if not GEMINI_API_KEYS:
        raise ValueError("No GEMINI_API_KEYS configured.")
    key = GEMINI_API_KEYS[_KEY_INDEX % len(GEMINI_API_KEYS)]
    _KEY_INDEX += 1
    return key


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


def save_md_backup(filename: str, text: str) -> Path:
    """Save OCR output as human-readable .md file in md_backup/."""
    stem = Path(filename).stem
    out_path = MD_BACKUP_DIR / f"{stem}.md"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def _client() -> genai.Client:
    return genai.Client(api_key=_get_key())


def _upload_pdf(client: genai.Client, pdf_bytes: bytes, filename: str = "document.pdf"):
    """Upload PDF bytes to Gemini File API. Returns uploaded file object."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        uploaded = client.files.upload(
            file=tmp_path,
            config={"mime_type": "application/pdf", "display_name": filename},
        )
        while uploaded.state.name == "PROCESSING":
            time.sleep(1)
            uploaded = client.files.get(name=uploaded.name)
        if uploaded.state.name == "FAILED":
            raise RuntimeError(f"Gemini file processing failed: {uploaded.name}")
        return uploaded
    finally:
        os.unlink(tmp_path)


def _cleanup(client: genai.Client, uploaded_file) -> None:
    try:
        client.files.delete(name=uploaded_file.name)
    except Exception:
        pass


def classify(pdf_bytes: bytes) -> dict:
    """Phase 1: Classify document type."""
    client = _client()
    uploaded = _upload_pdf(client, pdf_bytes)
    try:
        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=[_CLASSIFY_PROMPT, uploaded],
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
    finally:
        _cleanup(client, uploaded)


def extract(pdf_bytes: bytes, file_id: str, filename: str, doc_type: str) -> str:
    """Phase 2: Extract full content with type-specific schema."""
    client = _client()

    schema_fields = _SCHEMA.get(doc_type, _SCHEMA["default"]).strip()
    prompt = _EXTRACT_PROMPT_TEMPLATE.format(
        filename=filename,
        schema_fields=schema_fields,
        file_id=file_id,
    )

    uploaded = _upload_pdf(client, pdf_bytes, filename=filename)
    try:
        response = client.models.generate_content_stream(
            model=GEMINI_FLASH_MODEL,
            contents=[prompt, uploaded],
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

        return text
    finally:
        _cleanup(client, uploaded)


def pdf_to_markdown(
    pdf_bytes: bytes,
    file_id: str,
    filename: str = "document.pdf",
    force: bool = False,
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

    # Phase 2: Extract
    text = extract(pdf_bytes, file_id=file_id, filename=filename, doc_type=doc_type)

    # Cross-check doc_number against filename (filename is authoritative for the numeric part)
    text = _fix_doc_number_from_filename(text, filename)

    # Cross-check date against filename's DDMMYY segment (filename is authoritative)
    text = _fix_date_from_filename(text, filename)

    # Inject pipeline-generated fields into frontmatter
    ocr_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    page_count = _get_page_count(pdf_bytes)
    text = _inject_frontmatter_fields(text, {
        "page_count": page_count,
        "ocr_engine": GEMINI_FLASH_MODEL,
        "ocr_date": ocr_date,
        "status": "active",
        "status_note": "unverified",
    })

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
