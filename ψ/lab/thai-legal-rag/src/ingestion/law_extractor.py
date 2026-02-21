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
# Detect section marker at start of line (for splitting only).
# Negative lookahead excludes cross-references like "มาตรา ๑๓ หรือมาตรา ๑๔":
# after the number, if the same line continues with หรือ/และ/ถึง/วรรค (horizontal
# whitespace only — [^\S\n]* — so we don't cross to the next line), it's a reference,
# not a section header.  Fixes ghost-section bug where cross-refs at line-start were
# parsed as new section boundaries.
_SECTION_START_RE = re.compile(
    r"^(?:มาตรา|ข้อ)\s+[๐-๙\d]+(?:/[๐-๙\d]+)?\b(?![^\S\n]*(?:หรือ|และ|ถึง|วรรค|มาตรา|ข้อ))",
    re.MULTILINE,
)


@dataclass
class LawSection:
    """One มาตรา or ข้อ with its position in the hierarchy."""
    number: str                      # Arabic, e.g. "60" or "60/1"
    label: str                       # Original label, e.g. "มาตรา ๖๐" or "ข้อ ๑๗๐"
    text: str                        # Full text of this section
    part: str = ""                   # e.g. "ภาค ๓ การบริหารสัญญาและการตรวจรับพัสดุ"
    chapter: str = ""                # e.g. "หมวด ๖ การบริหารสัญญา"
    paragraphs: list = field(default_factory=list)  # วรรค 1, 2, 3... (content only, no label)
    references: list = field(default_factory=list)  # cross-section refs


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

# Minimum content chars to attempt Gemini paragraph splitting
_PARA_GEMINI_MIN_CHARS = 300

_LIST_ITEM_RE = re.compile(r"^\([ก-ฮ๐-๙\d]+\)")
# Detect list markers at the START OF A LINE within a (possibly multi-line) paragraph.
# Intentionally does NOT match inline cross-references like "ตาม (๑) (๒) และ (๓)"
# where the marker appears mid-sentence — those are references, not list items.
# Fix issue #6: only line-start markers indicate list structure.
_EMBEDDED_LIST_RE = re.compile(r"(?m)(?:^|\n)\s*\([ก-ฮ๐-๙\d]+\)")
# Definition list items: "คำ" หมายความว่า / หมายถึง — treated as list items
# Matches both ASCII quotes (") and Unicode curly quotes (\u201c\u201d).
# Allows optional content between closing quote and หมายความว่า
# (e.g. "(Electronic Catalog : e-catalog) หมายความว่า").
_DEFINITION_ITEM_RE = re.compile(
    r'^[\u201c"][^\u201d"]*[\u201d"].{0,60}?(หมายความว่า|หมายถึง|หมายรวมถึง)', re.UNICODE
)

# Definite new-paragraph starters: Thai legal subjects/authorities that virtually
# never appear as word-wrap continuation of a list item — only as sentence openers.
# When one of these appears inside a list-item block (no blank line), it signals
# the start of a closing legal paragraph (new วรรค).
_DEFINITE_SUBJECT_RE = re.compile(
    r"^(รัฐมนตรี|คณะกรรมการ|คณะรัฐมนตรี|ประธาน|ผู้ว่าราชการ|อธิบดี|นายก|ปลัด"
    r"|หัวหน้า|ผู้อํานวยการ|ผู้อำนวยการ|กรมการ|ผู้บัญชาการ)",
    re.UNICODE,
)


def _split_paragraphs_gemini(content: str) -> list[str] | None:
    """Use Gemini to split section content into วรรค.

    Args:
        content: Section text WITHOUT the label line (มาตรา XX / ข้อ XX).

    Returns:
        List of paragraph strings if successful and >1 paragraph found, else None.
    """
    if not GEMINI_API_KEYS:
        return None
    try:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEYS[0])
        prompt = (
            "แบ่งข้อความกฎหมายไทยต่อไปนี้เป็นวรรค (paragraph) ตามโครงสร้างราชกิจจานุเบกษา\n\n"
            "กฎการรวม (ห้ามแยก — สำคัญมาก):\n"
            "- อนุมาตรา (๑)(๒)(๓) และ sub-items (ก)(ข)(ค) ทุกระดับ เป็นส่วนหนึ่งของวรรคที่นำมา ห้ามแยกเป็นวรรคใหม่\n"
            "- \"เว้นแต่\" + อนุมาตราทั้งหมดที่ตามมา ((๑)...(ก)-(ซ) และ (๒)...(ก)-(ซ)) = วรรคเดียวกับประโยคหลัก\n"
            "- ตัวอย่าง: \"ให้ใช้วิธี...ก่อน เว้นแต่ (๑)...(ก)...(ซ) (๒)...(ก)...(ซ)\" = ทั้งหมดเป็นวรรคเดียว\n\n"
            "กฎการแยก (ต้องแยกเป็นวรรคใหม่):\n"
            "- เฉพาะประโยคอิสระที่ไม่ใช่อนุมาตราหรือ sub-item เท่านั้น\n"
            "- ประโยคที่ขึ้นต้นด้วย \"รัฐมนตรี\", \"ในกรณี\", \"ให้หน่วยงาน\", \"การยกเว้น\", \"กรณีตาม\" = วรรคใหม่\n\n"
            "รูปแบบคำตอบ:\n"
            "- JSON array of strings เท่านั้น ห้ามมี markdown หรือคำอธิบาย\n"
            "- แต่ละ element = 1 วรรค ไม่ต้องใส่เลขวรรค\n\n"
            f"ข้อความ:\n{content}"
        )
        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=prompt,
        )
        raw = (response.text or "").strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw.strip())
        parsed = json.loads(raw)
        if isinstance(parsed, list) and all(isinstance(p, str) for p in parsed):
            result = [p.strip() for p in parsed if p.strip()]
            if len(result) >= 1:
                return result
    except Exception as e:
        logger.debug(f"Gemini paragraph split failed: {e}")
    return None


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


_CONTINUATION_RE = re.compile(
    # "เพื่อ" removed (issue #5): it frequently starts independent วรรค in Thai law
    # e.g. "เพื่อให้การดำเนินงาน..." — a new legal sentence, not a continuation.
    # "ในราชกิจจา" added: "ในราชกิจจานุเบกษา" is always a prepositional complement
    # (e.g. "...นับแต่วันประกาศ\nในราชกิจจานุเบกษาเป็นต้นไป") — never a new วรรค.
    # "ให้เป็นไปตาม" added: predicate clause that completes a subject sentence split by
    # PDF blank lines (e.g. "รายละเอียด...ในหมวดนี้\nให้เป็นไปตามระเบียบ...") — never starts a วรรค.
    # "ประกอบด้วย" added: always a hanging predicate ("consists of") completing the
    # previous subject sentence (e.g. "ให้มีคณะกรรมการ...\nประกอบด้วย (๑)...").
    # "จากนั้น" added: sequence connector ("after that") continuing the same provision.
    # "นับแต่" added: temporal preposition ("counting from") never starts a new วรรค;
    # always completes a deadline clause split by PDF word-wrap
    # (e.g. "ภายในเจ็ดวันทำการ\nนับแต่วันประกาศ...").
    r"^(ตาม|แต่|และ|หรือ|เว้นแต่|โดย|ซึ่ง|ที่|แห่ง|ในราชกิจจา|ให้เป็นไปตาม|ทั้งนี้|ประกอบด้วย|จากนั้น|นับแต่)"
)

# Broader continuation patterns valid only inside list-context blocks.
# These phrases commonly appear as qualifiers/conditions within sub-items
# (e.g. "ทั้งนี้ การซื้อ...", "ในกรณีที่ผู้ยื่น...") but NOT as new วรรค openers.
_LIST_CONTEXT_CONTINUATION_RE = re.compile(
    r"^(ทั้งนี้|ในกรณี|ในการ|ในกระบวนการ"
    r"|ตาม|แต่|และ|หรือ|เว้นแต่|โดย|ซึ่ง|ที่|แห่ง|เพื่อ)"
)


def _has_list_markers_ahead(paragraphs: list[str], from_idx: int) -> bool:
    """Check if any paragraph from from_idx onward has list or definition markers."""
    for p in paragraphs[from_idx:]:
        s = p.strip()
        if s and (
            _LIST_ITEM_RE.match(s)
            or _EMBEDDED_LIST_RE.search(s)
            or _DEFINITION_ITEM_RE.match(s)
        ):
            return True
    return False


def _post_merge_paragraphs(paragraphs: list[str]) -> list[str]:
    """Post-process วรรค list: merge list items and orphan fragments back.

    Pass 1 — List-context merging with look-ahead:
    Once a list-item marker is seen (standalone, embedded, or definition-list item),
    enter list context. While in list context, use look-ahead to decide merging:
      - If subsequent paragraphs still contain list/definition markers → merge
      - If no markers ahead but paragraph starts with continuation pattern → merge
      - If no markers ahead and not continuation → exit list context (new วรรค)
    Always exit on _DEFINITE_SUBJECT_RE regardless.

    Definition list items ("คำ" หมายความว่า) are treated as list items — they
    always merge into the preceding paragraph and enter list context. This handles
    บทนิยาม sections (มาตรา/ข้อ 4) where each definition should be 1 วรรค total.

    Pass 2 — Orphan continuations: paragraphs starting with continuation words
    (ตาม, แต่, และ, etc.) that aren't independent sentences get merged back.
    """
    if len(paragraphs) <= 1:
        return paragraphs

    # Pass 1: merge list items and their continuation text into parent
    merged: list[str] = [paragraphs[0]]
    in_list_context = bool(_EMBEDDED_LIST_RE.search(paragraphs[0]))
    for idx, para in enumerate(paragraphs[1:], 1):
        stripped = para.strip()
        if not stripped:
            continue
        if _DEFINITION_ITEM_RE.match(stripped):
            # Definition list item ("คำ" หมายความว่า) — always merge into previous
            merged[-1] = merged[-1] + "\n" + para
            in_list_context = True
        elif _LIST_ITEM_RE.match(stripped):
            # Standalone list marker — merge and enter/stay in list context
            merged[-1] = merged[-1] + "\n" + para
            in_list_context = True
        elif in_list_context:
            if _DEFINITE_SUBJECT_RE.match(stripped):
                # Definite new วรรค — always exit
                in_list_context = False
                merged.append(para)
            elif _EMBEDDED_LIST_RE.search(stripped):
                # Current paragraph itself has list markers → still in block
                merged[-1] = merged[-1] + "\n" + para
            elif _has_list_markers_ahead(paragraphs, idx + 1):
                # More list items coming → between items → merge
                merged[-1] = merged[-1] + "\n" + para
            elif _LIST_CONTEXT_CONTINUATION_RE.match(stripped):
                # No more markers, but continuation/qualifier pattern → merge
                merged[-1] = merged[-1] + "\n" + para
            else:
                # No markers ahead, not continuation → list is done → new วรรค
                in_list_context = False
                merged.append(para)
        else:
            merged.append(para)
            # Check if this paragraph has embedded list markers → enter context
            if _EMBEDDED_LIST_RE.search(stripped):
                in_list_context = True

    # Pass 2: merge orphan continuation fragments
    result: list[str] = [merged[0]]
    for para in merged[1:]:
        stripped = para.strip()
        if stripped and _CONTINUATION_RE.match(stripped):
            # Continuation word at start — merge into previous paragraph
            result[-1] = result[-1] + "\n" + para
        else:
            result.append(para)

    return result


def _split_paragraphs(section_text: str) -> list[str]:
    """Split a section's text into วรรค (paragraphs).

    Strategy: Gemini first, blank-line split as fallback.
    - Gemini handles all semantic boundary detection (วรรค, list merging, etc.)
    - Blank-line split is used only when Gemini is unavailable or fails.
    """
    lines = section_text.strip().splitlines()
    # Drop the label prefix but preserve any inline content on the same line.
    # e.g. "ข้อ ๒ ระเบียบนี้ให้ใช้บังคับ..." → keep "ระเบียบนี้ให้ใช้บังคับ..."
    if lines and _SECTION_START_RE.match(lines[0].strip()):
        m = _SECTION_START_RE.match(lines[0].strip())
        inline = lines[0].strip()[m.end():].strip()
        content_lines = ([inline] if inline else []) + lines[1:]
    else:
        content_lines = lines
    # Strip page headers before any splitting
    content = _strip_page_headers("\n".join(content_lines))

    # Collapse triple+ newlines (artifacts from page header stripping) before Gemini
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Gemini: always use for semantic paragraph splitting
    gemini_result = _split_paragraphs_gemini(content)
    if gemini_result:
        return _post_merge_paragraphs(gemini_result)

    # Fallback: blank-line split (when Gemini unavailable or failed)
    # Pre-process: join single-newline lines that are mid-sentence (no sentence-
    # ending punctuation, no section/list marker) to reduce false blank-line
    # breaks caused by PDF formatting newlines.
    joined_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            # Preserve blank lines (they become split points)
            joined_lines.append("")
        elif (joined_lines
              and joined_lines[-1]  # prev line is non-blank
              and not _LIST_ITEM_RE.match(stripped)
              and not _SECTION_START_RE.match(stripped)):
            # Mid-sentence continuation — join to previous line
            joined_lines[-1] = joined_lines[-1] + " " + stripped
        else:
            joined_lines.append(stripped)
    content = "\n".join(joined_lines)

    raw_paras = re.split(r"\n(?:[ \t]*\n)+", content)
    paragraphs: list[str] = []
    for para in raw_paras:
        para = para.strip()
        if not para:
            continue
        if paragraphs and _LIST_ITEM_RE.match(para):
            merged, tail = _split_list_para(para, paragraphs[-1])
            paragraphs[-1] = merged
            if tail:
                paragraphs.append(tail)
        else:
            paragraphs.append(para)

    return _post_merge_paragraphs(paragraphs)


# ── Cross-reference extraction ─────────────────────────────────────────────────

_XREF_RE = re.compile(r"(?:มาตรา|ข้อ)\s+([๐-๙\d]+(?:/[๐-๙\d]+)?)")

def _extract_references(section_text: str, own_number: str) -> list[dict]:
    """Extract cross-section references from section text.

    Returns list of {"type": str, "section": str, "text": str}
    where type is one of: subordinate_to, mutatis_mutandis, references.
    """
    results: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for m in _XREF_RE.finditer(section_text):
        raw_num = m.group(1)
        section_num = _to_arabic(raw_num)

        # Skip self-references
        if section_num == own_number:
            continue

        # Look at surrounding text for classification
        # Check ~30 chars before the match start
        start = max(0, m.start() - 30)
        preceding = section_text[start:m.start()]
        # Check ~30 chars after the match end
        following = section_text[m.end():m.end() + 30]

        if "ภายใต้บังคับ" in preceding:
            ref_type = "subordinate_to"
        elif "โดยอนุโลม" in preceding or "โดยอนุโลม" in following:
            ref_type = "mutatis_mutandis"
        else:
            ref_type = "references"

        # Skip internal paragraph refs (วรรคหนึ่ง, วรรคสอง, etc.)
        # These are caught by the regex if embedded like "มาตรา ๕๖ วรรคหนึ่ง"
        # but we still want the section ref itself — only skip if it's own number

        key = (ref_type, section_num)
        if key not in seen:
            seen.add(key)
            matched_text = section_text[m.start():m.end()]
            results.append({
                "type": ref_type,
                "section": section_num,
                "text": matched_text,
            })

    return results


# ── Trailing structure trimmer ─────────────────────────────────────────────────

# Structural header that is ALWAYS a section/part divider (never inline content)
_STRUCT_PART_RE = re.compile(r"^ส่วนที่\s+[๐-๙\d]+\s*$")
_STRUCT_PHAK_RE = re.compile(r"^ภาค(?:\s*ที่)?\s+[๐-๙\d]+\s*$")
# หมวด is structural ONLY when standalone (no continuation text after the title)
_STRUCT_CHAPTER_RE = re.compile(r"^หมวด(?:\s*ที่)?\s+[๐-๙\d]+\s*$")

# Thai sentence-final words — when a line ends with one of these (optionally
# followed by spaces/trailing whitespace), the sentence is complete and the
# following short non-legal line is a structural heading, not a continuation.
_SENTENCE_FINAL_RE = re.compile(
    r"(?:ได้|แล้ว|ต่อไป|ต่อไปได้|ไป|ไว้|นั้น|นี้|ด้วย|เท่านั้น|ทันที|โดยเร็ว|อนุโลม|กำหนด|กําหนด)\s*$"
)

# Signature/closing block markers that appear at the end of Thai law documents.
# Everything from these markers to the end of the section text should be trimmed
# (they belong to the document footer, not the last มาตรา/ข้อ).
_SIGNATURE_BLOCK_RE = re.compile(
    r"^(?:ผู้รับสนองพระราชโองการ|หมายเหตุ\s*:-|หมายเหตุ\s*:|ประกาศ\s+ณ\s+วัน)"
)

# Legal content markers — lines containing these are real legal text, not titles
_LEGAL_CONTENT_MARKERS = re.compile(
    # "ข้อ" requires a following space+number to avoid matching compound words
    # like "ข้อความ", "ข้อตกลง", "ข้อเสนอ" as false legal-content triggers.
    r"(มาตรา|ข้อ\s+[๐-๙\d]|วรรค|พ\.ร\.บ\.|พระราชบัญญัติ|ระเบียบ|ให้|ต้อง|ห้าม|กรณี|ตาม|แห่ง)"
)


def _trim_trailing_structure(section_text: str) -> str:
    """Strip trailing structural headers (ส่วนที่, หมวด, ภาค) from section text.

    These headers belong to the next chapter/part, not to the current section.
    They get captured because _parse_sections() takes all lines between two
    section markers (มาตรา/ข้อ), which may include structural headers that
    appear between the end of one section's content and the start of the next.

    Critical: Does NOT strip หมวด when it's an inline reference
    (e.g. "หมวด ๓ หรือหมวด ๔ แล้วแต่กรณี").
    """
    lines = section_text.splitlines()

    # Fast-path: trim signature/closing block (ผู้รับสนองพระราชโองการ, หมายเหตุ :-, ประกาศ ณ).
    # These markers only appear at the very end of a Thai law document (inside
    # the last มาตรา/ข้อ) and must be stripped wholesale.
    for idx, line in enumerate(lines):
        if idx == 0:
            continue  # never trim the label line
        if _SIGNATURE_BLOCK_RE.match(line.strip()):
            trimmed = "\n".join(lines[:idx]).strip()
            if trimmed:
                return trimmed
            break  # degenerate: label-only section, fall through to normal trim

    # Fast-path: trim trailing chapter/section header block.
    # The bottom-up scan cannot reach structural headers (หมวด/ส่วน) when
    # intervening chapter-title lines contain legal markers like "ให้"
    # (e.g. "การลงโทษให้เป็นผู้ทิ้งงาน" stops the scan before reaching "หมวด ๘").
    # Solution: scan the last 12 lines top-down for the TOPMOST standalone structural
    # header, then trim from there (removing that header and everything below it).
    # _STRUCT_*_RE requires the line to be ONLY the header (e.g. "หมวด ๘") so
    # inline references like "ตามหมวด ๕ หรือหมวด ๖" are safe (they have extra text).
    _TAIL_SCAN = 12
    tail_start = max(1, len(lines) - _TAIL_SCAN)  # never trim the label line
    for tail_abs in range(tail_start, len(lines)):
        tl = lines[tail_abs].strip()
        if (_STRUCT_CHAPTER_RE.match(tl) or _STRUCT_PART_RE.match(tl)
                or _STRUCT_PHAK_RE.match(tl)):
            # Found topmost structural header in tail window — trim from here
            trimmed = "\n".join(lines[:tail_abs]).strip()
            if trimmed:
                return trimmed
            break  # degenerate: structural header right after label

    # Scan from bottom: collect a candidate trim block.
    # The block may contain structural headers + title lines + blanks.
    # We trim if:
    #   (a) the block contains at least one formal structural header (หมวด/ส่วน/ภาค), OR
    #   (b) all collected non-blank trailing lines are non-legal AND short (≤ 30 chars),
    #       indicating a standalone topic heading between sections (common in ระเบียบ).
    # Once we find a structural header, we stop scanning upward when we
    # hit a line with legal content (to avoid eating real section text).
    found_structural = False
    found_nonlegal_trailing = False
    trim_from = len(lines)
    i = len(lines) - 1
    while i >= 1:  # never trim the first line (section label)
        stripped = lines[i].strip()

        # Skip blank lines
        if not stripped:
            i -= 1
            continue

        # Structural header — confirms this block should be trimmed
        if (_STRUCT_PART_RE.match(stripped)
                or _STRUCT_CHAPTER_RE.match(stripped)
                or _STRUCT_PHAK_RE.match(stripped)):
            found_structural = True
            trim_from = i
            i -= 1
            continue

        # If we already found a structural header, stop at any content line
        # (don't eat real section text above the structural header)
        if found_structural:
            break

        # Non-legal short line — candidate for standalone topic heading
        # (e.g. "คณะกรรมการซื้อหรือจ้าง", "วิธีประกาศเชิญชวนทั่วไป")
        # Guards:
        #   - list items like (๑)(ก) are content, not headers
        #   - only mark as trailing heading if the previous content line ends
        #     with a sentence-final word (ได้/แล้ว/ต่อไป/...) so we don't
        #     accidentally trim word-wrapped continuations ("มีอำนาจสั่งยกเลิก")
        # Either way: continue scanning (don't break) — a structural header
        # above may still trigger the trim via the found_structural path.
        if (not _LEGAL_CONTENT_MARKERS.search(stripped)
                and len(stripped) <= 30
                and not _LIST_ITEM_RE.match(stripped)):
            prev_j = i - 1
            while prev_j >= 0 and not lines[prev_j].strip():
                prev_j -= 1
            prev_stripped = lines[prev_j].strip() if prev_j >= 0 else ""
            prev_is_sentence_final = bool(prev_stripped and _SENTENCE_FINAL_RE.search(prev_stripped))
            prev_is_list_item = bool(prev_stripped and _LIST_ITEM_RE.match(prev_stripped))
            if prev_is_sentence_final or prev_is_list_item:
                found_nonlegal_trailing = True
                trim_from = i
            i -= 1
            continue

        # Legal content line or long non-legal line — stop scanning
        break

    should_trim = (found_structural or found_nonlegal_trailing) and trim_from < len(lines)
    if should_trim:
        # Also trim trailing blank lines before the structural block
        while trim_from > 1 and not lines[trim_from - 1].strip():
            trim_from -= 1
        return "\n".join(lines[:trim_from]).strip()

    return section_text


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
        section_text = _trim_trailing_structure(section_text)

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
            references=_extract_references(section_text, number),
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


# ── Per-section MD files ───────────────────────────────────────────────────────

def _section_filename(law_type: str, number: str) -> str:
    """Generate a per-section filename, e.g. มาตรา_056.md or ขอ_056.md."""
    prefix = "มาตรา" if law_type == "พระราชบัญญัติ" else "ข้อ"
    # Handle inserted sections like "60/1" → "060_1"
    if "/" in number:
        main, sub = number.split("/", 1)
        padded = f"{int(main):03d}_{sub}" if main.isdigit() else f"{main}_{sub}"
    else:
        padded = f"{int(number):03d}" if number.isdigit() else number
    return f"{prefix}_{padded}.md"


def _build_section_md(doc: LawDocument, sec: LawSection) -> str:
    """Build markdown text for a single section file with YAML frontmatter."""
    # Build context header: [law_short_name | part | chapter | มาตรา X]
    ctx_parts = [doc.law_short_name or doc.law_name]
    if sec.part:
        ctx_parts.append(sec.part)
    if sec.chapter:
        ctx_parts.append(sec.chapter)
    section_label = f"มาตรา {sec.number}" if doc.law_type == "พระราชบัญญัติ" else f"ข้อ {sec.number}"
    ctx_parts.append(section_label)
    context_header = "[" + " | ".join(ctx_parts) + "]"

    # Strip any page header artifacts that survived into section text (e.g. from old cache)
    section_text = _strip_page_headers(sec.text)

    # Escape double quotes in YAML string values
    def _esc(s: str) -> str:
        return s.replace('"', '\\"')

    lines = [
        "---",
        f'law_name: "{_esc(doc.law_name)}"',
        f'law_short_name: "{_esc(doc.law_short_name)}"',
        f'law_type: "{doc.law_type}"',
        f'law_year_be: "{doc.law_year_be}"',
        f'part: "{_esc(sec.part)}"',
        f'chapter: "{_esc(sec.chapter)}"',
        f'section: "{sec.number}"',
        f"total_paragraphs: {len(sec.paragraphs)}",
    ]

    # Add references to frontmatter
    if sec.references:
        lines.append("references:")
        for ref in sec.references:
            lines.append(f'  - type: {ref["type"]}')
            lines.append(f'    section: "{ref["section"]}"')

    lines += [
        f'file_id: "{doc.file_id}"',
        f'file_url: "https://drive.google.com/file/d/{doc.file_id}/view"',
        f'status: "active"',
        "---",
        "",
        context_header,
        "",
    ]

    # Reference block (before วรรค content)
    if sec.references:
        # Group by type
        by_type: dict[str, list[str]] = {}
        for ref in sec.references:
            by_type.setdefault(ref["type"], []).append(ref["text"])
        type_labels = {
            "subordinate_to": "ภายใต้บังคับ",
            "mutatis_mutandis": "โดยอนุโลม",
            "references": "อ้างอิง",
        }
        for rtype, label in type_labels.items():
            if rtype in by_type:
                lines.append(f"> **{label}**: {', '.join(by_type[rtype])}")
        lines.append("")

    # Hybrid วรรค display: show per-paragraph headings when >1 วรรค
    if len(sec.paragraphs) > 1:
        for i, para in enumerate(sec.paragraphs, 1):
            lines.append(f"### วรรค {i}")
            lines.append(_strip_page_headers(para))
            lines.append("")
    else:
        lines.append(section_text)
        lines.append("")
    return "\n".join(lines)


def _save_section_files(doc: LawDocument) -> Path:
    """Write one MD file per section into {MD_BACKUP_DIR}/{stem}/."""
    stem = Path(doc.filename).stem
    sections_dir = MD_BACKUP_DIR / stem
    sections_dir.mkdir(parents=True, exist_ok=True)

    for sec in doc.sections:
        fname = _section_filename(doc.law_type, sec.number)
        out_path = sections_dir / fname
        out_path.write_text(_build_section_md(doc, sec), encoding="utf-8")

    logger.info(f"Section files saved: {sections_dir} ({len(doc.sections)} files)")
    return sections_dir


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
            sections = []
            for s in cached["sections"]:
                s.setdefault("references", [])
                sections.append(LawSection(**s))
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
             "part": s.part, "chapter": s.chapter, "paragraphs": s.paragraphs,
             "references": s.references}
            for s in sections
        ],
        "full_text": text,
        "ocr_engine": ocr_engine,
        "total_sections": len(sections),
    })

    # Save MD backup (full) + per-section files
    md_path = _save_md_backup(doc)
    logger.debug(f"Law MD backup saved: {md_path}")
    _save_section_files(doc)

    return doc
