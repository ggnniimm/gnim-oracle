# Lesson: Don't Fill Retrieval Gaps with Own Reasoning

**Date**: 2026-02-24
**Source**: thai-legal-rag — กวจ. 5529 session (งดหรือลดค่าปรับ case)

## Pattern

When retrieval returns chunks but none clearly answer the question, an LLM acting as a Thai legal assistant faces a temptation: fill the gap with its own legal reasoning. This is dangerous.

**What happened**: Previous session retrieved chunks about "งดหรือลดค่าปรับ" but กวจ. 5529 wasn't indexed yet. The LLM hedged but I supplemented with reasoning: "ไม่ได้". This was wrong. When กวจ. 5529 was indexed, the document showed the opposite for กรณีที่ 2: "ได้" (under ม. 102 discretion).

## The Rule

When retrieved chunks don't conclusively answer the question:
- Say: **"ข้อมูลที่มีไม่เพียงพอในการตอบคำถามนี้"**
- Do NOT substitute with own legal reasoning, even if it seems logical
- Especially critical in Thai procurement law where case distinctions are precise

## Why It's Dangerous

Thai legal documents distinguish cases explicitly. A general rule ("งดค่าปรับไม่ได้หลังผ่อนปรน") may have exceptions documented only in specific หารือ letters. Without the source document, any answer is speculation — and wrong speculation in legal context can cause real harm.

## Meta-search Lesson

When searching for a specific file in Google Drive:
- Use `list_files()` + name filter for targeted lookup
- Don't rely on `list_pdfs()` dry-run (finds all PDFs in folder — easy to miss if previous dry-run had different scope)

## Document Number Not Searchable

OCR extracts text from PDF pages — reference numbers in letterheads often get misread (5529 → 55). BM25/FAISS search content, not metadata. Queries like "มีหนังสือเลข 5529..." will never work.

**Fix direction**: Prepend `[doc_number | date | issuer]` to chunk text during indexing — makes reference numbers content-searchable.

## Tags

`retrieval-gap`, `legal-reasoning`, `don't-fill-gaps`, `source-required`, `doc-number-search`, `thai-legal-rag`
