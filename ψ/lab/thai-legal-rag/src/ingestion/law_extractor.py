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
    number: str                      # Arabic, e.g. "60" or "60/1"
    label: str                       # Original label, e.g. "มาตรา ๖๐" or "ข้อ ๑๗๐"
    text: str                        # Full text of this section
    part: str = ""                   # e.g. "ภาค ๓ การบริหารสัญญาและการตรวจรับพัสดุ"
    chapter: str = ""                # e.g. "หมวด ๖ การบริหารสัญญา"
    paragraphs: list = field(default_factory=list)  # วรรค 1, 2, 3... (content only, no label)


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
    # Law title may span multiple lines, e.g.:
    #   พระราชบัญญัติ\nการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ\nพ.ศ. ๒๕๖๐
    # Strategy: find law_type keyword, then collect lines until พ.ศ. line (inclusive)
    head = text[:3000]
    law_name = ""
    lines_head = head.splitlines()
    for i, line in enumerate(lines_head):
        if law_type in line.strip():
            # Collect this line + next lines until we hit พ.ศ. or blank / มาตรา
            parts = [line.strip()]
            for j in range(i + 1, min(i + 5, len(lines_head))):
                next_line = lines_head[j].strip()
                if not next_line:
                    break
                parts.append(next_line)
                if "พ.ศ." in next_line:
                    break
                if re.match(r"^(มาตรา|ข้อ|หมวด|ภาค)", next_line):
                    parts.pop()
                    break
            law_name = " ".join(parts)
            law_name = re.sub(r"\s+", " ", law_name).strip()
            break
    if not law_name:
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


# ── Text cleaner ───────────────────────────────────────────────────────────────

def _strip_page_headers(text: str) -> str:
    """Remove ราชกิจจานุเบกษา page stamps interspersed in law text.

    Pattern (4 lines):
        หน้า   ๑๔
        เล่ม   ๑๓๔   ตอนที่   ๒๔   ก
        ราชกิจจานุเบกษา
        ๒๔   กุมภาพันธ์   ๒๕๖๐
    """
    text = re.sub(
        r"หน้า[ \t]+[๐-๙\d]+[^\n]*\n[^\n]*เล่ม[^\n]*\n[^\n]*ราชกิจจานุเบกษา[^\n]*\n[^\n]*\n?",
        "\n",
        text,
    )
    # Collapse runs of blank/whitespace-only lines left by stripping
    text = re.sub(r"\n[ \t]*\n[ \t]*\n", "\n\n", text)
    return text


# ── Text normalizer ────────────────────────────────────────────────────────────

def _normalize_section_headers(text: str) -> str:
    """Join มาตรา/ข้อ with number when the number appears on the next line.

    Some PDFs (e.g. single-digit มาตรา 1-9) format as:
        มาตรา \n๑ \n...
    while later sections use:
        มาตรา ๑๐ ...
    This normalises both to the same inline format before section parsing.
    """
    return re.sub(
        r"^((?:มาตรา|ข้อ))\s*\n[ \t]*([๐-๙\d]+(?:/[๐-๙\d]+)?)",
        r"\1 \2",
        text,
        flags=re.MULTILINE,
    )


# ── Paragraph splitter ─────────────────────────────────────────────────────────

_LIST_ITEM_RE = re.compile(r"^\([ก-ฮ๐-๙\d]+\)")

# Definite new-paragraph starters: Thai legal subjects/authorities that virtually
# never appear as word-wrap continuation of a list item — only as sentence openers.
# When one of these appears inside a list-item block (no blank line), it signals
# the start of a closing legal paragraph (new วรรค).
_DEFINITE_SUBJECT_RE = re.compile(
    r"^(รัฐมนตรี|คณะกรรมการ|คณะรัฐมนตรี|ประธาน|ผู้ว่าราชการ|อธิบดี|นายก|ปลัด"
    r"|หัวหน้า|ผู้อํานวยการ|ผู้อำนวยการ|กรมการ|ผู้บัญชาการ)",
    re.UNICODE,
)


def _split_list_para(para: str, prev_varak: str) -> tuple[str, str | None]:
    """Given a para that starts with a list marker, split into (list_part, tail_varak).

    The list_part gets merged into prev_varak.
    tail_varak is the trailing content that starts a new legal paragraph (if any).

    Thai law PDFs sometimes attach the closing วรรค of a section directly to the
    last list item without a blank line, e.g.:
        (ซ) กรณีอื่นตามที่กำหนดในกฎกระทรวง
        รัฐมนตรีอาจออกกฎกระทรวง...    ← new วรรค, but no blank line!

    We detect this only when a line starts with a known Thai legal authority/subject
    (_DEFINITE_SUBJECT_RE) — words that virtually never appear as word-wrap
    continuation of a list item. This avoids false positives from word-wrapped lines
    like `การคัดเลือก` or `จำหน่าย  ก่อสร้าง`.
    """
    para_lines = para.splitlines()
    list_lines: list[str] = []
    tail_lines: list[str] = []
    after_list = False

    for pline in para_lines:
        stripped = pline.strip()
        if not stripped:
            continue
        if after_list:
            tail_lines.append(pline)
        elif _LIST_ITEM_RE.match(stripped):
            # Another list marker — stays in list part
            list_lines.append(pline)
        elif _DEFINITE_SUBJECT_RE.match(stripped):
            # A definite new-paragraph subject — this is the start of a new วรรค
            after_list = True
            tail_lines.append(pline)
        else:
            # Word-wrap continuation of the current list item
            list_lines.append(pline)

    list_part = prev_varak + "\n" + "\n".join(list_lines) if list_lines else prev_varak
    tail_varak = "\n".join(tail_lines).strip() if tail_lines else None
    return list_part, tail_varak


def _split_paragraphs(section_text: str) -> list[str]:
    """Split a section's text into วรรค (paragraphs).

    Rules:
    - Skips the label line (มาตรา XX / ข้อ XX)
    - Splits by blank/whitespace-only lines
    - Merges list items (ก)(ข)(ค) or (๑)(๒)(๓) back into the preceding วรรค
    - Detects trailing non-continuation content inside a list-item block and
      splits it off as a new วรรค (handles the case where the closing paragraph
      is attached to the last list item with no blank line)
    """
    lines = section_text.strip().splitlines()
    # Drop the label line
    content_lines = lines[1:] if lines and _SECTION_START_RE.match(lines[0].strip()) else lines
    # Split by blank/whitespace-only lines
    content = "\n".join(content_lines)
    raw_paras = re.split(r"\n(?:[ \t]*\n)+", content)

    paragraphs: list[str] = []
    for para in raw_paras:
        para = para.strip()
        if not para:
            continue
        if paragraphs and _LIST_ITEM_RE.match(para):
            # Merge list item into previous วรรค, but detect trailing new-paragraph content
            merged, tail = _split_list_para(para, paragraphs[-1])
            paragraphs[-1] = merged
            if tail:
                paragraphs.append(tail)
        else:
            paragraphs.append(para)

    return paragraphs


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
            paragraphs=_split_paragraphs(section_text),
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

        # Prepend context so each embedded chunk knows which law/chapter it belongs to
        ctx_parts = [doc.law_short_name]
        if sec.part:
            ctx_parts.append(sec.part)
        if sec.chapter:
            ctx_parts.append(sec.chapter)
        context_line = "[" + " | ".join(ctx_parts) + "]"
        lines += ["", context_line, sec.text, ""]

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

    # Strip ราชกิจจาฯ page stamps before parsing
    text = _strip_page_headers(text)

    # Normalize section headers before parsing
    text = _normalize_section_headers(text)

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
             "part": s.part, "chapter": s.chapter, "paragraphs": s.paragraphs}
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
