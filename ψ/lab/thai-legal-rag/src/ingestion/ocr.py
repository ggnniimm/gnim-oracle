"""
Gemini Vision OCR.
Converts PDF bytes → markdown text via Gemini multimodal.

Flow:
  pdf_bytes
    → list of page images (PyMuPDF)
    → each page → Gemini vision call (base64 image)
    → concatenate pages → full text
    → cache result by file_id hash
"""
import base64
import hashlib
import json
import logging
from pathlib import Path

import fitz  # PyMuPDF
import google.generativeai as genai

from src.config import (
    GEMINI_API_KEYS,
    GEMINI_FLASH_MODEL,
    OCR_CACHE_DIR,
    OCR_MIN_CHARS_PER_PAGE,
)

logger = logging.getLogger(__name__)

_KEY_INDEX = 0


def _get_api_key() -> str:
    """Round-robin key rotation."""
    global _KEY_INDEX
    if not GEMINI_API_KEYS:
        raise ValueError("No GEMINI_API_KEYS configured.")
    key = GEMINI_API_KEYS[_KEY_INDEX % len(GEMINI_API_KEYS)]
    _KEY_INDEX += 1
    return key


def _ocr_page_image(image_bytes: bytes, page_num: int) -> str:
    """Send a single page image to Gemini Vision, return extracted text."""
    api_key = _get_api_key()
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(GEMINI_FLASH_MODEL)

    prompt = (
        "อ่านข้อความจากหน้าเอกสารราชการไทยนี้ทั้งหมด "
        "ให้ถูกต้องและครบถ้วน ห้ามแต่งเติมหรือสรุปเอง "
        "ถ้ามีตารางให้แสดงเป็น markdown table "
        "ถ้ามีหัวข้อให้ใส่ ## นำหน้า "
        "ตอบเฉพาะข้อความที่อ่านได้เท่านั้น"
    )

    image_part = {
        "mime_type": "image/png",
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }

    try:
        response = model.generate_content([prompt, image_part])
        return response.text.strip()
    except Exception as e:
        logger.warning(f"OCR failed for page {page_num}: {e}")
        return ""


def _cache_path(file_id: str) -> Path:
    h = hashlib.sha256(file_id.encode()).hexdigest()[:16]
    return OCR_CACHE_DIR / f"{h}.json"


def _load_cache(file_id: str) -> str | None:
    p = _cache_path(file_id)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("text")
    return None


def _save_cache(file_id: str, text: str) -> None:
    p = _cache_path(file_id)
    p.write_text(
        json.dumps({"file_id": file_id, "text": text}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def pdf_to_text(pdf_bytes: bytes, file_id: str, force: bool = False) -> str:
    """
    Main OCR entry point.
    - Checks cache first (by file_id).
    - Extracts text layer from PDF (fast path).
    - Falls back to Gemini Vision for pages with sparse text.
    - Caches and returns full markdown text.
    """
    if not force:
        cached = _load_cache(file_id)
        if cached is not None:
            logger.debug(f"OCR cache hit: {file_id}")
            return cached

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text: list[str] = []

    for page_num, page in enumerate(doc):
        # Try native text extraction first
        native_text = page.get_text("text").strip()

        if len(native_text) >= OCR_MIN_CHARS_PER_PAGE:
            pages_text.append(f"<!-- page {page_num + 1} -->\n{native_text}")
            logger.debug(f"Page {page_num + 1}: native text ({len(native_text)} chars)")
        else:
            # Render page as image → Gemini Vision OCR
            logger.debug(
                f"Page {page_num + 1}: sparse text ({len(native_text)} chars) → OCR"
            )
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR quality
            pix = page.get_pixmap(matrix=mat)
            image_bytes = pix.tobytes("png")
            ocr_text = _ocr_page_image(image_bytes, page_num + 1)
            pages_text.append(f"<!-- page {page_num + 1} (ocr) -->\n{ocr_text}")

    doc.close()
    full_text = "\n\n".join(pages_text)
    _save_cache(file_id, full_text)
    return full_text
