"""
Query expansion for Thai legal search.
Uses Gemini Flash to generate relevant legal keywords from a user query.
"""
import logging

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
            logger.debug(f"Expanded '{query}' → {len(result)} terms")
            return result
    except Exception as e:
        logger.warning(f"Query expansion failed: {e}")

    return [query]
