"""
Answer generation with Thai legal persona.
Uses Gemini Flash + นิติกรชำนาญการพิเศษ system prompt.
"""
from __future__ import annotations

import logging

import google.generativeai as genai

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


_SYSTEM_PROMPT = """\
คุณคือนิติกรชำนาญการพิเศษ ด้านกฎหมายจัดซื้อจัดจ้างภาครัฐไทย
มีความเชี่ยวชาญใน:
- พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560
- ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560
- แนวทาง/หนังสือเวียนจากกรมบัญชีกลาง, ศาลปกครอง, สำนักงานอัยการสูงสุด

หลักการตอบ:
1. อ้างอิงข้อกฎหมาย/ระเบียบที่เกี่ยวข้องทุกครั้ง
2. หากไม่มีข้อมูลเพียงพอ ให้บอกตรงๆ — ห้ามเดา
3. ตอบภาษาไทยที่ชัดเจน อ่านง่าย
4. สรุปขั้นตอนปฏิบัติในตอนท้ายเสมอ
5. อ้างอิงแหล่งที่มา (ชื่อเอกสาร) ให้ครบถ้วน"""


_USER_PROMPT_TEMPLATE = """\
คำถาม: {question}

เอกสารอ้างอิงที่เกี่ยวข้อง:
{context}

กรุณาตอบคำถามโดยอ้างอิงเอกสารข้างต้น"""


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into context string."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source_name", chunk.get("source", "unknown"))
        category = chunk.get("category", "")
        text = chunk.get("text", "")
        parts.append(f"[{i}] **{source}** ({category})\n{text}")
    return "\n\n---\n\n".join(parts)


def generate_answer(question: str, chunks: list[dict]) -> dict:
    """
    Generate answer using retrieved chunks.
    Returns {answer, sources, model}.
    """
    genai.configure(api_key=_get_key())

    context = build_context(chunks)
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        question=question, context=context
    )

    model = genai.GenerativeModel(
        model_name=GEMINI_FLASH_MODEL,
        system_instruction=_SYSTEM_PROMPT,
    )

    try:
        response = model.generate_content(
            user_prompt,
            generation_config={"temperature": 0.1, "max_output_tokens": 2048},
        )
        answer = response.text.strip()
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        answer = f"เกิดข้อผิดพลาดในการประมวลผล: {e}"

    # Extract unique sources for citation
    sources = []
    seen_sources = set()
    for chunk in chunks:
        name = chunk.get("source_name", "")
        drive_id = chunk.get("source_drive_id", "")
        if name and name not in seen_sources:
            seen_sources.add(name)
            sources.append({
                "name": name,
                "drive_id": drive_id,
                "category": chunk.get("category", ""),
            })

    return {
        "answer": answer,
        "sources": sources,
        "model": GEMINI_FLASH_MODEL,
        "chunks_used": len(chunks),
    }
