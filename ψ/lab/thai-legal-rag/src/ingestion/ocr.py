"""
Gemini Vision OCR — two-phase agentic approach.

Phase 1: Classify document type (Ruling_Committee, Ruling_Court, etc.)
Phase 2: Extract full content with type-specific YAML frontmatter schema

Uses Gemini File API (upload_file) — sends PDF directly to Gemini,
no page rendering needed. Much higher quality than image-based OCR.

Cache: SHA256(file_id) → JSON (skip re-OCR on repeat runs)
"""
import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path

import google.generativeai as genai

from src.config import (
    GEMINI_API_KEYS,
    GEMINI_FLASH_MODEL,
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

# Type-specific frontmatter schema instructions
_SCHEMA = {
    "Ruling_Committee": """
    - type: "ข้อหารือ กวจ."
    - date: "YYYY-MM-DD" (จากหัวเอกสาร)
    - ref_number: "เลขที่หนังสือ เช่น ที่ กค (กวจ) 0405.4/XXXXX"
    - topic: "เรื่อง (subject line เต็ม)"
    - signer: "ชื่อผู้ลงนาม"
    - tags: [list of relevant Thai legal keywords]
    - law_section: [list of specific laws/articles referenced, e.g. "พ.ร.บ.จัดซื้อฯ มาตรา 93"]
    """,
    "Ruling_Court": """
    - type: "คำพิพากษาศาลปกครอง"
    - date: "YYYY-MM-DD"
    - ref_number: "เลขคดี"
    - topic: "เรื่อง"
    - court: "ชื่อศาล เช่น ศาลปกครองสูงสุด"
    - tags: [list of relevant Thai legal keywords]
    - law_section: [list of laws/articles referenced]
    """,
    "Ruling_AttorneyGeneral": """
    - type: "ข้อหารืออัยการสูงสุด"
    - date: "YYYY-MM-DD"
    - ref_number: "เลขที่หนังสือ"
    - topic: "เรื่อง"
    - signer: "ชื่อผู้ลงนาม"
    - tags: [list of relevant Thai legal keywords]
    - law_section: [list of laws/articles referenced]
    """,
    "Circular": """
    - type: "หนังสือเวียน"
    - date: "YYYY-MM-DD"
    - ref_number: "เลขที่ ว..."
    - topic: "เรื่อง"
    - signer: "ชื่อผู้ลงนาม"
    - tags: [list of relevant Thai legal keywords]
    - law_section: [list of laws/articles referenced]
    """,
    "default": """
    - type: "อื่นๆ"
    - date: "YYYY-MM-DD"
    - ref_number: "เลขที่อ้างอิง"
    - topic: "หัวข้อ/เรื่อง"
    - tags: []
    - law_section: []
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
source_file: {filename}
{schema_fields}
file_id: "{file_id}"
file_url: "https://drive.google.com/file/d/{file_id}/view"
---

# [title from document]

## ข้อเท็จจริง
[facts section verbatim]

## ประเด็นข้อหารือ
[issues/questions]

## ข้อวินิจฉัย
[ruling/judgment — full text verbatim]

## สรุปข้อวินิจฉัย
[brief bullet-point summary]

## ข้อกฎหมายที่เกี่ยวข้อง
[list of laws with descriptions]

**Rules:**
- Extract ALL text verbatim — do NOT summarize or omit
- Preserve tables as markdown tables
- Output raw Markdown only — NO code fences (no ```)
- YAML values with special chars must be quoted
- tags and law_section must be YAML lists
"""


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


def _upload_pdf(pdf_bytes: bytes, filename: str = "document.pdf"):
    """Upload PDF bytes to Gemini File API. Returns uploaded file object."""
    genai.configure(api_key=_get_key())

    # Write to temp file (File API requires a file path)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        uploaded = genai.upload_file(tmp_path, mime_type="application/pdf")
        # Wait for processing
        while uploaded.state.name == "PROCESSING":
            time.sleep(1)
            uploaded = genai.get_file(uploaded.name)
        if uploaded.state.name == "FAILED":
            raise RuntimeError(f"Gemini file processing failed: {uploaded.name}")
        return uploaded
    finally:
        os.unlink(tmp_path)


def _cleanup(uploaded_file) -> None:
    try:
        uploaded_file.delete()
    except Exception:
        pass


def classify(pdf_bytes: bytes) -> dict:
    """Phase 1: Classify document type."""
    genai.configure(api_key=_get_key())
    model = genai.GenerativeModel(GEMINI_FLASH_MODEL)

    uploaded = _upload_pdf(pdf_bytes)
    try:
        response = model.generate_content(
            [_CLASSIFY_PROMPT, uploaded],
            generation_config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        logger.debug(f"Classified: {result.get('type')} ({result.get('confidence', 0)*100:.0f}%)")
        return result
    except Exception as e:
        logger.warning(f"Classification failed: {e}")
        return {"type": "Unknown", "confidence": 0.0}
    finally:
        _cleanup(uploaded)


def extract(pdf_bytes: bytes, file_id: str, filename: str, doc_type: str) -> str:
    """Phase 2: Extract full content with type-specific schema."""
    genai.configure(api_key=_get_key())
    model = genai.GenerativeModel(GEMINI_FLASH_MODEL)

    schema_fields = _SCHEMA.get(doc_type, _SCHEMA["default"]).strip()
    prompt = _EXTRACT_PROMPT_TEMPLATE.format(
        filename=filename,
        schema_fields=schema_fields,
        file_id=file_id,
    )

    uploaded = _upload_pdf(pdf_bytes, filename=filename)
    try:
        response = model.generate_content([prompt, uploaded], stream=True)
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

        return text
    finally:
        _cleanup(uploaded)


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

    result = {
        "text": text,
        "doc_type": doc_type,
        "category": DOC_TYPE_CATEGORY.get(doc_type, "อื่นๆ"),
        "confidence": confidence,
        "file_id": file_id,
        "filename": filename,
    }

    _save_cache(file_id, result)
    return result
