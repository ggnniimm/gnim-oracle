"""
Answer generation with Thai legal persona.
Uses Gemini Flash + นิติกรชำนาญการพิเศษ system prompt.
"""
from __future__ import annotations

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
5. อ้างอิงแหล่งที่มา (ชื่อเอกสาร) ให้ครบถ้วน
6. กฎหมายบางฉบับมีหลายเวอร์ชัน (มีการแก้ไขหรือยกเลิก) — หากเอกสารอ้างอิงมีหลายฉบับในปี พ.ศ. ต่างกัน ให้ยึดฉบับที่มี พ.ศ. สูงสุด (ล่าสุด) เป็นหลัก และแจ้งผู้ถามด้วยว่าฉบับเก่าถูกแก้ไข/ยกเลิกแล้ว
7. หากเอกสารระบุกรณี รายการ หรือประเภทชัดเจน (เช่น "ครอบคลุม:", "ได้แก่", หน้าที่ตามข้อย่อย) ให้แสดงครบทุกรายการในคำตอบ ห้ามย่อรวมหรือตัดออก
8. หากเอกสารอ้างอิงระบุข้อยกเว้นหรือเงื่อนไขสำคัญ (เช่น "ไม่ต้องรอ...", "สามารถดำเนินการได้โดยไม่ต้อง...", "ดู กวจ. ...") ให้ระบุในคำตอบเสมอ — ข้อยกเว้นเหล่านี้มีความสำคัญต่อการปฏิบัติ
9. หากเอกสารอ้างอิงมีหลายฉบับและแต่ละฉบับระบุหน้าที่หรือข้อกำหนดเพิ่มเติมที่แตกต่างกัน ให้สรุปหน้าที่/ข้อกำหนดจากทุกเอกสารที่เกี่ยวข้อง ห้ามละเว้นเอกสารใดเอกสารหนึ่ง
10. หากเอกสารอ้างอิงระบุตัวเลข ระยะเวลา หรือจำนวนเงินที่เป็นสาระสำคัญ (เช่น "2 ปี", "ไม่น้อยกว่า ๒ ปี", "500,000 บาท") ให้ระบุตัวเลขนั้นในคำตอบเสมอ — ห้ามละเว้นหรือสรุปรวมโดยไม่ระบุตัวเลข
11. ใช้ศัพท์ทางกฎหมายตามที่ปรากฏในเอกสารอ้างอิง เช่น "ข้อเสนอ" (ไม่ใช่ "ใบเสนอราคา"), "หัวหน้าหน่วยงานของรัฐ" (ไม่ใช่ "ผู้บริหาร"), "ผู้ยื่นข้อเสนอ" (ไม่ใช่ "ผู้เสนอราคา") — ห้ามแปลงเป็นคำทั่วไป"""


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
        ref = chunk.get("ref_number", "")
        date = chunk.get("date", "")
        law_year_be = chunk.get("law_year_be", "")
        text = chunk.get("text", "")

        header_parts = [f"**{source}**"]
        if ref:
            header_parts.append(f"เลขที่ {ref}")
        if date:
            header_parts.append(f"ลว. {date}")
        if law_year_be:
            header_parts.append(f"พ.ศ. {law_year_be}")

        header = " | ".join(header_parts)
        parts.append(f"[{i}] {header} ({category})\n{text}")
    return "\n\n---\n\n".join(parts)


def generate_answer(question: str, chunks: list[dict]) -> dict:
    """
    Generate answer using retrieved chunks.
    Returns {answer, sources, model}.
    """
    client = genai.Client(api_key=_get_key())

    context = build_context(chunks)
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        question=question, context=context
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=user_prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=4096,
            ),
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
