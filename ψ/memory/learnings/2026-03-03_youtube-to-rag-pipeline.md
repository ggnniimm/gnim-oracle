# YouTube-to-RAG Pipeline Pattern

**Date**: 2026-03-03
**Source**: Facebook post about creating personal AI bot from YouTube content
**Tags**: rag, data-sourcing, knowledge-extraction, notebooklm

## Pattern

Use YouTube transcripts as domain-specific data source for RAG bots:
1. Chrome Extension "YouTube to NotebookLM" bulk-imports transcripts
2. 3-step prompt extraction in NotebookLM
3. Export structured knowledge for RAG/bot

## 3-Step Knowledge Extraction Prompt

### Step 1: Master Outline
- Role: Data Architect
- "กางสารบัญกลยุทธ์ทั้งหมด ยังไม่ต้องอธิบาย เอาแค่โครงสร้าง"
- Purpose: See the full knowledge map before diving in

### Step 2: Deep-dive (Zero Summarization)
- Go topic-by-topic from the outline
- Rule: "ห้ามสรุปย่อ เอาแบบละเอียดทุกเม็ด"
- Force If-Then logic format for actionable knowledge
- This pattern is useful for legal domain: "ถ้าค่าปรับเกิน 10% → ต้องบอกเลิกสัญญา"

### Step 3: Glossary
- List all domain-specific terms with definitions
- Ensures bot understands specialized vocabulary
- Applicable to กวจ terms: ผ่อนปรน, ทิ้งงาน, เหมารวม

## Relevance to thai-legal-rag

- Zero Summarization = our generator rule 7 ("ห้ามย่อรวมหรือตัดออก")
- If-Then format could improve answer actionability
- Glossary concept → query expansion / terminology normalization
- Master Outline → auto-anchor structure extraction
