"""
Query expansion for Thai legal search.
Uses Gemini Flash to generate relevant legal keywords from a user query.
"""
import logging
import re

from google import genai
from google.genai import types as genai_types

from src.config import GEMINI_API_KEYS, GEMINI_FLASH_MODEL

logger = logging.getLogger(__name__)

_KEY_INDEX = 0


def _get_key() -> str:
    global _KEY_INDEX
    if not GEMINI_API_KEYS:
        raise ValueError("No GEMINI_API_KEYS configured.")
    key = GEMINI_API_KEYS[_KEY_INDEX % len(GEMINI_API_KEYS)]
    _KEY_INDEX += 1
    return key


_EXPAND_PROMPT = """\
คุณเป็นผู้เชี่ยวชาญกฎหมายจัดซื้อจัดจ้างภาครัฐไทย

จากคำถามต่อไปนี้ ให้สร้างคำสำคัญที่เกี่ยวข้องสำหรับการค้นหาเอกสารราชการ:
คำถาม: {query}

ให้ตอบเป็น JSON array ของ string เท่านั้น เช่น:
["คำ1", "คำ2", "คำ3"]

รวมถึง:
- ศัพท์เทคนิคทางกฎหมาย (พ.ร.บ., ระเบียบ, หนังสือเวียน)
- ชื่อหน่วยงาน (กรมบัญชีกลาง, ศาลปกครอง, สำนักงานอัยการสูงสุด)
- ขั้นตอนและกระบวนการที่เกี่ยวข้อง
ตอบ JSON เท่านั้น ห้ามมีข้อความอื่น:"""


# Patterns that indicate a specific, targeted query — expansion hurts precision
_SPECIFIC_PATTERNS = [
    r"ข้อ\s*[\d๐-๙]+",            # ข้อ 11, ข้อ ๑๑
    r"มาตรา\s*[\d๐-๙]+",          # มาตรา 60, มาตรา ๖๐
    r"วรรค\s*(หนึ่ง|สอง|สาม|สี่|ห้า|\d+)",  # วรรคหนึ่ง, วรรค 2
    r"กฎกระทรวง.*(ฉบับที่|พ\.ศ\.)",          # กฎกระทรวงฉบับที่ 2 / พ.ศ. 2560
    r"หมวด\s*[\d๐-๙]+",           # หมวด 3
    r"\b\d{4,}\b",                 # bare 4+ digit number = doc ID lookup (e.g. 5529, 51349)
]


def is_specific_query(query: str) -> bool:
    """Return True if query targets a specific provision — expansion hurts precision."""
    return any(re.search(p, query) for p in _SPECIFIC_PATTERNS)


def expand_query(query: str) -> list[str]:
    """
    Given a user query, return list of expanded Thai legal keywords.
    Falls back to [query] if expansion fails.
    """
    client = genai.Client(api_key=_get_key())

    try:
        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=_EXPAND_PROMPT.format(query=query),
            config=genai_types.GenerateContentConfig(temperature=0.2),
        )
        text = response.text.strip()
        # Strip markdown code blocks if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        import json
        keywords = json.loads(text)
        if isinstance(keywords, list):
            result = [query] + [k for k in keywords if isinstance(k, str)]
            result = result[:6]  # cap at 6 queries — more causes generic terms to dominate
            logger.debug(f"Expanded '{query}' → {len(result)} terms")
            return result
    except Exception as e:
        logger.warning(f"Query expansion failed: {e}")

    return [query]
