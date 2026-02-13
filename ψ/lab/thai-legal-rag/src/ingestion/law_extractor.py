"""
Thai Law Document Extractor.

Two-phase extraction:
1. PyMuPDF  — fast text extraction for selectable PDFs (ราชกิจจานุเบกษา standard)
2. Gemini   — fallback for scanned/image PDFs

Parses Thai law hierarchy:
  ภาค  → หมวด  → มาตรา/ข้อ

Outputs structured section list + saves MD backup.
Supports:
  - พระราชบัญญัติ  (มาตรา)
  - ระเบียบ         (ข้อ)
  - กฎกระทรวง      (ข้อ)
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import tempfile
import time
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.config import (
    GEMINI_API_KEYS,
    GEMINI_FLASH_MODEL,
    MD_BACKUP_DIR,
    OCR_CACHE_DIR,
    OCR_MIN_CHARS_PER_PAGE,
)

logger = logging.getLogger(__name__)

# ── Thai/Arabic numeral helpers ────────────────────────────────────────────────
_THAI_TO_ARABIC = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

def _to_arabic(s: str) -> str:
    return s.translate(_THAI_TO_ARABIC)

# ── Hierarchy regex ────────────────────────────────────────────────────────────
# Match both Thai and Arabic numerals, optional chapter name on same line
_PART_RE    = re.compile(r"^(ภาค(?:\s*ที่)?\s*[๐-๙\d]+(?:\s+[^\n]+)?)", re.MULTILINE)
_CHAPTER_RE = re.compile(r"^(หมวด(?:\s*ที่)?\s*[๐-๙\d]+(?:\s+[^\n]+)?)", re.MULTILINE)
_SECTION_RE = re.compile(
    r"^((?:มาตรา|ข้อ)\s+[๐-๙\d]+(?:/[๐-๙\d]+)?)\s*\n?(.*?)(?=^(?:มาตรา|ข้อ)\s+[๐-๙\d]|\Z)",
    re.MULTILINE | re.DOTALL,
)
# Detect section marker at start of line (for splitting only)
_SECTION_START_RE = re.compile(r"^(?:มาตรา|ข้อ)\s+[๐-๙\d]+", re.MULTILINE)


@dataclass
class LawSection:
    """One มาตรา or ข้อ with its position in the hierarchy."""
    number: str          # Arabic, e.g. "60" or "60/1"
    label: str           # Original label, e.g. "มาตรา ๖๐" or "ข้อ ๑๗๐"
    text: str            # Full text of this section
    part: str = ""       # e.g. "ภาค ๓ การบริหารสัญญาและการตรวจรับพัสดุ"
    chapter: str = ""    # e.g. "หมวด ๖ การบริหารสัญญา"


@dataclass
class LawDocument:
    """Parsed law document."""
    filename: str
    file_id: str
    law_name: str
    law_short_name: str
    law_type: str                    # "พระราชบัญญัติ" | "ระเบียบ" | "กฎกระทรวง"
    law_year_be: str                 # e.g. "2560"
    sections: list[LawSection] = field(default_factory=list)
    full_text: str = ""
    ocr_engine: str = "pymupdf"
    total_sections: int = 0


# ── Law name / type detection ──────────────────────────────────────────────────

def _detect_law_meta(text: str, filename: str) -> tuple[str, str, str, str]:
    """
    Detect (law_name, law_short_name, law_type, law_year_be) from text + filename.

    Priority: filename keywords → first non-empty lines of text → defaults.
    This avoids false positives where a ระเบียบ body references พ.ร.บ. early on.
    """
    stem = Path(filename).stem.lower()

    # ── Step 1: law_type from filename (most reliable) ─────────────────────
    # "พรบ" must be checked before "ประกาศ" — "ประกาศราชกิจจา" is publication venue, not doc type
    if "พรบ" in stem or "พ.ร.บ" in stem:
        law_type = "พระราชบัญญัติ"
    elif "ระเบียบ" in stem:
        law_type = "ระเบียบ"
    elif "กฎกระทรวง" in stem:
        law_type = "กฎกระทรวง"
    elif "ประกาศ" in stem and "ราชกิจจา" not in stem:
        law_type = "ประกาศ"
    else:
        # Fall back to scanning first 300 chars (before body references other laws)
        head300 = text[:300]
        if "ระเบียบกระทรวง" in head300 or "ระเบียบ" in head300:
            law_type = "ระเบียบ"
        elif "กฎกระทรวง" in head300:
            law_type = "กฎกระทรวง"
        elif "พระราชบัญญัติ" in head300:
            law_type = "พระราชบัญญัติ"
        else:
            law_type = "กฎหมาย"

    # ── Step 2: BE year from text ──────────────────────────────────────────
    year_m = re.search(r"พ\.ศ\.\s*([๐-๙]{4}|\d{4})", text[:3000])
    law_year_be = _to_arabic(year_m.group(1)) if year_m else ""

    # ── Step 3: full law name ──────────────────────────────────────────────
    # Look for full name starting with law_type keyword (skip very short matches)
    head = text[:3000]
    # Collect all matches, pick the longest one that includes year
    candidates = re.findall(
        rf"({law_type}[^\n\r{{}}]+(?:พ\.ศ\.\s*[๐-๙\d]+)?)",
        head,
    )
    if candidates:
        # Prefer the FIRST candidate that includes พ.ศ. (= title line, not body)
        with_year = [c for c in candidates if "พ.ศ." in c]
        law_name = (with_year[0] if with_year else candidates[0]).strip()
        # Remove trailing artifacts
        law_name = re.sub(r"\s+", " ", law_name).strip()
    else:
        law_name = Path(filename).stem.replace("+", " ").replace("-", " ").strip()

    # ── Step 4: short name — derive from filename keywords (most reliable) ──
    suffix = f" {law_year_be}" if law_year_be else ""
    stem_clean = Path(filename).stem.lower()
    if "พรบ" in stem_clean or "พ.ร.บ" in stem_clean:
        if "จัดซื้อ" in stem_clean or "จัดซื้อจัดจ้าง" in law_name:
            law_short_name = f"พ.ร.บ.จัดซื้อจัดจ้างฯ{suffix}"
        else:
            law_short_name = f"พ.ร.บ.ฯ{suffix}"
    elif "ระเบียบ" in stem_clean:
        if "จัดซื้อ" in stem_clean or "จัดซื้อจัดจ้าง" in law_name or "จัดซื้อจัดจ้าง" in text[:1000]:
            law_short_name = f"ระเบียบฯ จัดซื้อจัดจ้าง{suffix}"
        else:
            law_short_name = f"ระเบียบฯ{suffix}"
    elif "กฎกระทรวง" in stem_clean:
        law_short_name = f"กฎกระทรวงฯ{suffix}"
    else:
        # Try text-based short name
        short_map = [
            ("พระราชบัญญัติการจัดซื้อจัดจ้าง",           f"พ.ร.บ.จัดซื้อจัดจ้างฯ{suffix}"),
            ("ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้าง", f"ระเบียบฯ จัดซื้อจัดจ้าง{suffix}"),
        ]
        law_short_name = law_name
        for key, short in short_map:
            if key in law_name:
                law_short_name = short
                break
        if law_short_name == law_name and len(law_short_name) < 8:
            law_short_name = f"{law_type}ฯ{suffix}"

    return law_name, law_short_name, law_type, law_year_be


# ── Text extraction ────────────────────────────────────────────────────────────

def _extract_pymupdf(pdf_bytes: bytes) -> tuple[str, int]:
    """Extract text using PyMuPDF. Returns (text, page_count)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages), len(pages)


def _is_text_good(text: str, page_count: int) -> bool:
    """Check if PyMuPDF extraction produced usable text."""
    if page_count == 0:
        return False
    avg_chars = len(text.strip()) / page_count
    return avg_chars >= OCR_MIN_CHARS_PER_PAGE


def _extract_gemini(pdf_bytes: bytes, filename: str) -> str:
    """Fallback: use Gemini Vision to extract law text."""
    from google import genai
    from google.genai import types as genai_types

    _KEY_INDEX = 0
    key = GEMINI_API_KEYS[0]
    client = genai.Client(api_key=key)

    prompt = """คุณคือผู้เชี่ยวชาญด้าน OCR สำหรับเอกสารราชการไทย
อ่านและคัดลอกข้อความจากกฎหมาย/ระเบียบฉบับนี้ทั้งหมด verbatim
รักษาโครงสร้าง ภาค หมวด มาตรา/ข้อ ให้ครบถ้วน
ห้ามสรุป ห้ามตัดทอน ห้ามแต่งเติม
Output raw text เท่านั้น ไม่ต้องมี markdown formatting"""

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

        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=[prompt, uploaded],
        )
        return response.text or ""
    finally:
        os.unlink(tmp_path)
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass


# ── Section parser ─────────────────────────────────────────────────────────────

def _parse_sections(text: str) -> list[LawSection]:
    """
    Parse law text into individual มาตรา/ข้อ sections with hierarchy metadata.
    """
    sections: list[LawSection] = []
    current_part = ""
    current_chapter = ""

    # Split text into lines for hierarchical scanning
    lines = text.splitlines()
    i = 0

    # We'll build a list of (line_index, type, content)
    # then assemble section texts
    markers: list[tuple[int, str, str]] = []  # (line_idx, kind, text)

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if _PART_RE.match(stripped):
            markers.append((idx, "part", stripped))
        elif _CHAPTER_RE.match(stripped):
            markers.append((idx, "chapter", stripped))
        elif _SECTION_START_RE.match(stripped):
            markers.append((idx, "section", stripped))

    # Extract section texts by finding spans between consecutive section markers
    section_marker_indices = [(idx, content) for idx, kind, content in markers if kind == "section"]

    for pos, (line_idx, label) in enumerate(section_marker_indices):
        # Find end of this section (start of next section marker)
        if pos + 1 < len(section_marker_indices):
            end_idx = section_marker_indices[pos + 1][0]
        else:
            end_idx = len(lines)

        section_lines = lines[line_idx:end_idx]
        section_text = "\n".join(section_lines).strip()

        # Determine which part/chapter this section belongs to
        # (last part/chapter marker before this line_idx)
        part = ""
        chapter = ""
        for m_idx, kind, content in markers:
            if m_idx >= line_idx:
                break
            if kind == "part":
                part = content
            elif kind == "chapter":
                chapter = content

        # Extract section number
        num_m = re.match(r"(?:มาตรา|ข้อ)\s+([๐-๙\d]+(?:/[๐-๙\d]+)?)", label)
        number = _to_arabic(num_m.group(1)) if num_m else label

        sections.append(LawSection(
            number=number,
            label=label,
            text=section_text,
            part=part,
            chapter=chapter,
        ))

    return sections


# ── MD backup ──────────────────────────────────────────────────────────────────

def _build_md_text(doc: LawDocument) -> str:
    """Build markdown text with YAML frontmatter for a law document."""
    ocr_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "---",
        f"original_filename: {doc.filename}",
        f'doc_type: "กฎหมาย"',
        f'law_name: "{doc.law_name}"',
        f'law_short_name: "{doc.law_short_name}"',
        f'law_type: "{doc.law_type}"',
        f'law_year_be: "{doc.law_year_be}"',
        f'source: "ราชกิจจานุเบกษา"',
        f'file_id: "{doc.file_id}"',
        f'file_url: "https://drive.google.com/file/d/{doc.file_id}/view"',
        f"total_sections: {doc.total_sections}",
        f'ocr_engine: "{doc.ocr_engine}"',
        f'ocr_date: "{ocr_date}"',
        f'status: "active"',
        "---",
        "",
        f"# {doc.law_name}",
        "",
    ]

    current_part = ""
    current_chapter = ""
    for sec in doc.sections:
        if sec.part != current_part:
            current_part = sec.part
            if current_part:
                lines += ["", f"## {current_part}", ""]
        if sec.chapter != current_chapter:
            current_chapter = sec.chapter
            if current_chapter:
                lines += ["", f"### {current_chapter}", ""]
        lines += ["", sec.text, ""]

    return "\n".join(lines)


def _save_md_backup(doc: LawDocument) -> Path:
    stem = Path(doc.filename).stem
    out_path = MD_BACKUP_DIR / f"{stem}.md"
    out_path.write_text(_build_md_text(doc), encoding="utf-8")
    return out_path


# ── Cache ──────────────────────────────────────────────────────────────────────

def _cache_path(file_id: str) -> Path:
    h = hashlib.sha256(file_id.encode()).hexdigest()[:16]
    return OCR_CACHE_DIR / f"law_{h}.json"


def _load_cache(file_id: str) -> Optional[dict]:
    p = _cache_path(file_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _save_cache(file_id: str, data: dict) -> None:
    p = _cache_path(file_id)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_law(
    pdf_bytes: bytes,
    file_id: str,
    filename: str,
    force: bool = False,
) -> LawDocument:
    """
    Main entry point. Extract and parse a Thai law PDF.

    Returns LawDocument with parsed sections and saves MD backup.
    Uses cache to skip re-extraction on repeat runs.
    """
    if not force:
        cached = _load_cache(file_id)
        if cached is not None:
            logger.debug(f"Law cache hit: {file_id}")
            sections = [LawSection(**s) for s in cached["sections"]]
            return LawDocument(
                filename=cached["filename"],
                file_id=cached["file_id"],
                law_name=cached["law_name"],
                law_short_name=cached["law_short_name"],
                law_type=cached["law_type"],
                law_year_be=cached["law_year_be"],
                sections=sections,
                full_text=cached.get("full_text", ""),
                ocr_engine=cached["ocr_engine"],
                total_sections=cached["total_sections"],
            )

    # Phase 1: Try PyMuPDF
    ocr_engine = "pymupdf"
    try:
        text, page_count = _extract_pymupdf(pdf_bytes)
        if not _is_text_good(text, page_count):
            logger.info(f"PyMuPDF text quality low ({len(text)} chars, {page_count} pages) — falling back to Gemini")
            text = _extract_gemini(pdf_bytes, filename)
            ocr_engine = "gemini"
        else:
            logger.info(f"PyMuPDF extracted {len(text)} chars from {page_count} pages")
    except Exception as e:
        logger.warning(f"PyMuPDF failed ({e}) — using Gemini")
        text = _extract_gemini(pdf_bytes, filename)
        ocr_engine = "gemini"

    # Detect law metadata
    law_name, law_short_name, law_type, law_year_be = _detect_law_meta(text, filename)
    logger.info(f"Detected: {law_type} '{law_short_name}' {law_year_be}")

    # Parse sections
    sections = _parse_sections(text)
    logger.info(f"Parsed {len(sections)} sections from '{filename}'")

    doc = LawDocument(
        filename=filename,
        file_id=file_id,
        law_name=law_name,
        law_short_name=law_short_name,
        law_type=law_type,
        law_year_be=law_year_be,
        sections=sections,
        full_text=text,
        ocr_engine=ocr_engine,
        total_sections=len(sections),
    )

    # Save cache
    _save_cache(file_id, {
        "filename": doc.filename,
        "file_id": doc.file_id,
        "law_name": doc.law_name,
        "law_short_name": doc.law_short_name,
        "law_type": doc.law_type,
        "law_year_be": doc.law_year_be,
        "sections": [
            {"number": s.number, "label": s.label, "text": s.text,
             "part": s.part, "chapter": s.chapter}
            for s in sections
        ],
        "full_text": text,
        "ocr_engine": ocr_engine,
        "total_sections": len(sections),
    })

    # Save MD backup
    md_path = _save_md_backup(doc)
    logger.debug(f"Law MD backup saved: {md_path}")

    return doc
