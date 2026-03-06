# OCR Summaries as Hallucination Vectors

**Date**: 2026-03-04
**Context**: กวจ 22315 — Gemini OCR added interpretive "เช่น" examples to บทสรุปสำหรับสืบค้น
**Tags**: rag, ocr, hallucination, data-quality, legal

## Pattern

When Gemini generates OCR output for legal documents, it appends a "บทสรุปสำหรับสืบค้น" (search summary) section. This summary sometimes **adds interpretive examples** that aren't present in the original document.

### What happened

กวจ 22315 ข้อวินิจฉัย says:
> "หากเป็นการแก้ไขในส่วนที่มิใช่รายละเอียดของเนื้องาน แม้จะมีการตรวจรับงานงวดสุดท้ายแล้วก็ย่อมสามารถกระทำได้"

But the Gemini-generated search summary added:
> "...แก้ไขได้ **เช่น การลดวงเงิน การเพิ่มระยะเวลาส่งมอบ** โดยต้องอยู่ภายในขอบข่าย..."

These examples don't appear in the วินิจฉัย. Gemini likely inferred them from มาตรา 97 วรรคสาม (which discusses เงิน/เวลา adjustments in general contract amendments) and conflated it with the separate post-inspection amendment principle.

### Why it's dangerous

1. The chunk containing the hallucinated examples gets **high retrieval scores** because it perfectly matches queries about post-inspection amendments
2. The generator trusts the chunk content and presents the examples as authoritative legal interpretation
3. No automated eval can catch this — only a domain expert who knows that ลดวงเงิน/เพิ่มเวลา inherently involve เนื้องาน changes

## Fix

- Remove interpretive additions from บทสรุปสำหรับสืบค้น
- Rebuild index
- Consider auditing all md files for similar OCR summary hallucinations

## Prevention

- Flag บทสรุปสำหรับสืบค้น sections with metadata so they can be deprioritized
- Or: only allow exact quotes from the document in search summaries, no interpretation
