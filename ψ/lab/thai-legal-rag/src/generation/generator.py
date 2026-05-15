"""
Answer generation with Thai legal persona.
Uses Gemini Flash + นิติกรชำนาญการพิเศษ system prompt.
"""
from __future__ import annotations

import logging
import os
import re

from google.genai import types as genai_types

from src.config import GEMINI_FLASH_MODEL, GEMINI_PRO_MODEL
from src.gemini_client import get_client, generate_with_retry

# If GENERATOR_MODEL is set, force that model for every query (experiments/rollback).
# Unset → smart routing: Pro for date-calc, Flash for the rest.
_FORCED_MODEL = os.getenv("GENERATOR_MODEL") or None

_THAI_MONTH_RE = re.compile(
    r"(?:มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|"
    r"กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)"
)


def _is_date_calc_query(q: str) -> bool:
    return "ค่าปรับ" in q and bool(_THAI_MONTH_RE.search(q))


def _pick_model(q: str) -> str:
    if _FORCED_MODEL:
        return _FORCED_MODEL
    return GEMINI_PRO_MODEL if _is_date_calc_query(q) else GEMINI_FLASH_MODEL

logger = logging.getLogger(__name__)


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
4. สรุปขั้นตอนปฏิบัติในตอนท้าย เฉพาะเมื่อคำถามถามถึงวิธีปฏิบัติหรือขั้นตอน — ถ้าคำถามถามเรื่องผลทางกฎหมาย หลักเกณฑ์ หรือคำนิยาม ให้ตอบตรงประเด็นโดยไม่ต้องสรุปขั้นตอน
5. อ้างอิงแหล่งที่มาด้วย [N] (ตัวเลขในวงเล็บเหลี่ยมตามหมายเลขที่กำหนดให้แต่ละเอกสาร) ทุกครั้งที่กล่าวถึงข้อมูลจากเอกสาร — ห้ามเขียนชื่อเอกสารในเนื้อหาคำตอบ ให้ใช้เฉพาะ [N] — ห้ามเขียนเลขอ้างอิงซ้ำติดกัน เช่น [2], [2], [3], [3] ผิด ให้เขียน [2], [3] เพียงครั้งเดียว — ห้ามสับสนระหว่างเลข [N] กับเลขเอกสารหรือเลขหนังสือที่ปรากฏในเนื้อหา เช่น ว ๔๗๖, ๕๑๔๑๙, ๒๓๐๙๔, ๑๕๓ — เลขเหล่านี้คือเลขอ้างอิงของหนังสือ ไม่ใช่เลข [N] ของเอกสารในชุดนี้ ให้ใช้เฉพาะหมายเลข [N] ที่ระบุไว้ด้านหน้าแต่ละเอกสารเท่านั้น
6. กฎหมายบางฉบับมีหลายเวอร์ชัน (มีการแก้ไขหรือยกเลิก) — หากเอกสารอ้างอิงมีหลายฉบับในปี พ.ศ. ต่างกัน ให้ยึดฉบับที่มี พ.ศ. สูงสุด (ล่าสุด) เป็นหลัก และแจ้งผู้ถามด้วยว่าฉบับเก่าถูกแก้ไข/ยกเลิกแล้ว
7. หากเอกสารระบุกรณี รายการ หรือประเภทชัดเจน (เช่น "ครอบคลุม:", "ได้แก่", หน้าที่ตามข้อย่อย) ให้แสดงครบทุกรายการในคำตอบ ห้ามย่อรวมหรือตัดออก
8. หากเอกสารอ้างอิงระบุเงื่อนไขเกี่ยวกับลำดับขั้นตอนหรือระยะเวลา เช่น "ไม่ต้องรอ..." "สามารถดำเนินการได้โดยไม่ต้อง..." "ก่อนที่จะ..." "ภายหลังจาก..." ให้ระบุในคำตอบเสมอ — ผู้ถามต้องการทราบว่าทำอะไรก่อนหลัง และต้องรอกระบวนการใดหรือไม่
9. หากเอกสารอ้างอิงมีหลายฉบับและแต่ละฉบับระบุหน้าที่หรือข้อกำหนดเพิ่มเติมที่แตกต่างกัน ให้สรุปหน้าที่/ข้อกำหนดจากทุกเอกสารที่เกี่ยวข้อง ห้ามละเว้นเอกสารใดเอกสารหนึ่ง
10. หากเอกสารอ้างอิงระบุตัวเลข ระยะเวลา หรือจำนวนเงินที่เป็นสาระสำคัญ (เช่น "2 ปี", "ไม่น้อยกว่า ๒ ปี", "500,000 บาท") ให้ระบุตัวเลขนั้นในคำตอบเสมอ — ห้ามละเว้นหรือสรุปรวมโดยไม่ระบุตัวเลข
11. ใช้ศัพท์ทางกฎหมายตามที่ปรากฏในเอกสารอ้างอิง เช่น "ข้อเสนอ" (ไม่ใช่ "ใบเสนอราคา"), "หัวหน้าหน่วยงานของรัฐ" (ไม่ใช่ "ผู้บริหาร"), "ผู้ยื่นข้อเสนอ" (ไม่ใช่ "ผู้เสนอราคา") — ห้ามแปลงเป็นคำทั่วไป
12. หากเอกสารอ้างอิงระบุรายละเอียดเชิงคุณภาพที่เป็นสาระสำคัญ เช่น ชีวิต, ทรัพย์สิน, ความปลอดภัย, ประโยชน์สาธารณะ ให้ระบุรายละเอียดเหล่านั้นในคำตอบเสมอ — ห้ามสรุปรวมเป็นคำกว้างๆ เช่น ห้ามเขียนแค่ พฤติการณ์ร้ายแรง หากเอกสารระบุว่า ความเสียหายร้ายแรงต่อชีวิตหรือทรัพย์สินของประชาชน
13. ตอบตรงคำถามที่ถาม — ถ้าคำถามถามว่า "ผลเป็นอย่างไร" หรือ "X คืออะไร" ให้ตอบเฉพาะผลทางกฎหมายหรือคำนิยามนั้น ไม่ต้องนำเสนอขั้นตอนหรือเรื่องที่เกี่ยวข้องซึ่งไม่ได้ถาม แม้เอกสารอ้างอิงจะมีข้อมูลเหล่านั้น — ใช้วิจารณญาณว่าอะไรคือสาระหลักของคำถาม
14. เมื่อเอกสารอ้างอิงระบุ มาตรา, ข้อ, หรือ วรรค ของกฎหมายหรือระเบียบ ที่เกี่ยวข้องโดยตรงกับคำถาม ให้ระบุหมายเลขมาตราหรือข้อนั้นในคำตอบเสมอ เช่น "ตามมาตรา 103" หรือ "ตามข้อ 183" — ห้ามอ้างเฉพาะชื่อ พ.ร.บ. โดยไม่ระบุมาตรา
15. ห้ามอ้างอิง [N] เอกสารที่ไม่มีข้อความนั้นอยู่จริง — ก่อน cite [N] ให้ตรวจสอบว่าข้อมูลนั้นปรากฏในเนื้อหาของเอกสาร [N] จริงๆ ห้ามนำ [N] ของเอกสาร rank สูงมาใส่แทนเพียงเพราะ rank สูงกว่าหรือหัวข้อใกล้เคียงกัน — ถ้าข้อมูลอยู่ใน [N] ที่ rank ต่ำ ให้ cite [N] นั้นตรงๆ
16. หากเนื้อหาของเอกสาร [N] มีข้อความเตือนว่า "ไม่ใช่หลักฐาน", "ห้ามอ้าง", "ไม่ใช่กรณี", "ไม่มีเนื้อหาเกี่ยวกับ", หรือ "⚠️" ระบุว่าเอกสารนั้นไม่ครอบคลุมกรณีใด ห้ามนำเอกสาร [N] นั้นไป cite สนับสนุนกรณีที่ถูกระบุว่าไม่ครอบคลุมโดยเด็ดขาด — ให้ใช้เฉพาะเอกสารอื่นที่มีเนื้อหาสนับสนุนกรณีนั้นจริงๆ
17. เมื่อคำถามเกี่ยวกับการคำนวณค่าปรับและมีการระบุวันที่จริง ให้คำนวณ step-by-step ดังนี้ และต้องแสดงทุก step ในคำตอบเสมอ แม้บางขั้นตอนจะไม่มีผลต่อตัวเลข: (1) ตรวจสอบวันครบกำหนด — ต้องระบุชัดเจนว่า "วันครบกำหนดตรงกับวันหยุด" หรือ "วันครบกำหนดเป็นวันทำการ" — ถ้าตรงวันหยุดให้เลื่อนเป็นวันทำการถัดไป ถ้าไม่ตรงให้ใช้วันนั้นเลย (2) ระบุกรณี: ส่งช้าครั้งเดียว / ส่งช้าไม่ผ่านส่งซ้ำ / ส่งก่อนกำหนดแต่ไม่ผ่าน (3) คำนวณ Gross = วันถัดจากกำหนด ถึงวันผ่านตรวจครั้งสุดท้าย (4) หักวันตรวจรับแต่ละครั้ง = วันถัดจากวันส่ง ถึงวันแจ้งผล/ผ่านตรวจ (5) แสดงสูตร: Gross − หักครั้งที่ 1 − หักครั้งที่ 2 = X วัน

ตัวอย่างการตอบที่ถูกต้อง:

ตัวอย่างที่ 1 — รักษาเงื่อนไขสำคัญ:
คำถาม: ภายหลังบอกเลิกสัญญา หน่วยงานต้องทำอย่างไร?
เอกสาร: "...สามารถจัดหาผู้รับจ้างรายใหม่ได้โดยไม่ต้องรอให้กระบวนการพิจารณาให้เป็นผู้ทิ้งงานสิ้นสุด..."
คำตอบที่ถูก: "สามารถจัดหาผู้รับจ้างรายใหม่ได้โดยไม่ต้องรอให้กระบวนการพิจารณาผู้ทิ้งงานสิ้นสุด"
คำตอบที่ผิด: "สามารถจัดหาผู้รับจ้างรายใหม่ได้ตามระเบียบฯ" (ตัดเงื่อนไข "ไม่ต้องรอ" ออก — ห้ามทำเช่นนี้)

ตัวอย่างที่ 2 — ตอบตรงผลทางกฎหมาย ไม่ขยายไปเรื่องขั้นตอน:
คำถาม: การส่งงานไม่ครบถ้วน แต่ตรวจรับงานไปแล้ว ผลเป็นอย่างไร?
เอกสาร: (1) ผู้รับจ้างยังต้องรับผิดในงานส่วนที่ขาด (2) หน่วยงานสามารถบอกเลิกสัญญาได้ (3) ภายหลังบอกเลิกสัญญา คู่สัญญาต้องกลับคืนสู่ฐานะเดิม
คำตอบที่ถูก: "การตรวจรับงานไม่ทำให้ผู้รับจ้างพ้นความรับผิด — ผู้รับจ้างยังต้องรับผิดในงานส่วนที่ยังไม่ได้ทำ"
คำตอบที่ผิด: "ผู้รับจ้างยังต้องรับผิด และหน่วยงานสามารถบอกเลิกสัญญาได้ และภายหลังบอกเลิกสัญญาต้องกลับคืนสู่ฐานะเดิม..." (ขยายไปเรื่องที่ไม่ได้ถาม — ห้ามทำเช่นนี้)"""


_USER_PROMPT_TEMPLATE = """\
คำถาม: {question}

เอกสารอ้างอิงที่เกี่ยวข้อง:
{context}

กรุณาตอบคำถามโดยอ้างอิงเอกสารข้างต้น"""


_RESCUE_PHRASES = [
    # (trigger, phrase_to_find_in_chunk, sentence_to_append, query_keywords)
    # query_keywords: at least one must appear in the query for the rescue to fire
    (
        "ไม่ต้องรอ",
        "ไม่ต้องรอให้กระบวนการพิจารณาให้เป็นผู้ทิ้งงาน",
        "**หมายเหตุ:** การจัดหาผู้รับจ้างรายใหม่สามารถดำเนินการได้โดยไม่ต้องรอให้กระบวนการพิจารณาให้เป็นผู้ทิ้งงานสิ้นสุด",
        ["ผู้ทิ้งงาน", "บอกเลิก", "จ้างรายใหม่"],
    ),
    (
        "ผ่านหัวหน้าเจ้าหน้าที่",
        "ผ่านหัวหน้าเจ้าหน้าที่",
        "**หมายเหตุ:** การรายงานผลต่อหัวหน้าหน่วยงานของรัฐต้องเสนอผ่านหัวหน้าเจ้าหน้าที่ ตามระเบียบกระทรวงการคลังฯ",
        ["หัวหน้าเจ้าหน้าที่", "รายงานผล", "ขั้นตอนการรายงาน"],
    ),
    (
        "ผลิตภายในประเทศ",
        "ผลิตภายในประเทศ",
        "**หมายเหตุ:** คณะกรรมการตรวจรับพัสดุมีหน้าที่ตรวจสอบว่าพัสดุที่ส่งมอบเป็นพัสดุที่ผลิตภายในประเทศตามเงื่อนไขสัญญา (หนังสือเวียน ว ๗๘)",
        ["ผลิตภายในประเทศ", "พัสดุไทย", "ว 78", "ว ๗๘"],
    ),
]


def _rescue_key_phrases(answer: str, chunks: list[dict], query: str = "") -> str:
    """If a key phrase exists in retrieved chunks but is missing from the
    answer, append it — only when the query is relevant."""
    all_text = " ".join(c.get("text", "") for c in chunks)
    for trigger, phrase, sentence, query_kws in _RESCUE_PHRASES:
        if phrase in all_text and trigger not in answer:
            if any(kw in query for kw in query_kws):
                answer = answer.rstrip() + "\n\n" + sentence
    return answer


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into context string, grouped by source.

    Numbering is per-document (not per-chunk) so the LLM cites [1] for
    all chunks from the same source instead of [1], [2], [3].
    """
    from collections import OrderedDict
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for chunk in chunks:
        key = chunk.get("source_name", chunk.get("source", "unknown"))
        grouped.setdefault(key, []).append(chunk)

    parts = []
    for doc_num, (source_name, doc_chunks) in enumerate(grouped.items(), 1):
        # Build header from first chunk's metadata
        first = doc_chunks[0]
        category = first.get("category", "")
        ref = first.get("ref_number", "")
        date = first.get("date", "")
        law_year_be = first.get("law_year_be", "")

        header_parts = [f"**{source_name}**"]
        if ref:
            header_parts.append(f"เลขที่ {ref}")
        if date:
            header_parts.append(f"ลว. {date}")
        if law_year_be:
            header_parts.append(f"พ.ศ. {law_year_be}")
        header = " | ".join(header_parts)

        # Combine all chunks from this document under one number
        combined_text = "\n\n".join(c.get("text", "") for c in doc_chunks)
        parts.append(f"[{doc_num}] {header} ({category})\n{combined_text}")
    return "\n\n---\n\n".join(parts)


def generate_answer(
    question: str,
    chunks: list[dict],
    history: list[dict] | None = None,
) -> dict:
    """
    Generate answer using retrieved chunks.
    history: list of {"role": "user"|"assistant", "content": str} from previous turns.
    Returns {answer, sources, model}.
    """
    client = get_client()

    context = build_context(chunks)
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        question=question, context=context
    )

    # Build multi-turn contents if history provided (last 6 turns = 3 exchanges)
    if history:
        contents: list = []
        for msg in history[-6:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(genai_types.Content(
                role=role,
                parts=[genai_types.Part(text=msg["content"])],
            ))
        contents.append(genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_prompt)],
        ))
    else:
        contents = user_prompt

    model = _pick_model(question)
    logger.info(f"Generator: {model}")

    try:
        response = generate_with_retry(
            client,
            model=model,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.0,
                max_output_tokens=8192,
            ),
        )
        answer = response.text.strip()
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        answer = f"เกิดข้อผิดพลาดในการประมวลผล: {e}"

    # Post-processing: rescue key phrases from chunks that LLM omitted
    answer = _rescue_key_phrases(answer, chunks, query=question)

    # Extract unique sources for citation
    sources = []
    seen_sources = set()
    for chunk in chunks:
        name = chunk.get("source_name", "")
        file_id = chunk.get("file_id", "")
        if name and name not in seen_sources:
            seen_sources.add(name)
            sources.append({
                "name": name,
                "file_id": file_id,
                "file_url": chunk.get("file_url", ""),
                "category": chunk.get("category", ""),
            })

    return {
        "answer": answer,
        "sources": sources,
        "model": model,
        "chunks_used": len(chunks),
    }
