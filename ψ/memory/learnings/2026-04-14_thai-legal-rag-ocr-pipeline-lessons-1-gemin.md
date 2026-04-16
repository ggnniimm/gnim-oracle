---
title: ## Thai Legal RAG OCR Pipeline Lessons
tags: [ocr, gemini, yaml, thai-legal, google-drive, oauth]
created: 2026-04-14
source: rrr: thai-legal-rag-ocr-pipeline 2026-02-13
---

# ## Thai Legal RAG OCR Pipeline Lessons

## Thai Legal RAG OCR Pipeline Lessons

1. **Gemini YAML frontmatter defense**: Gemini sometimes outputs YAML fields as `    - key: value` (list item) instead of `key: value` (flat). Fix with `_fix_frontmatter()` regex: `re.sub(r"^\s*-\s+(?=[a-zA-Z_]+:)", "", line)` before parsing.

2. **LLM verbatim extraction requires explicit instructions**: "copy verbatim" is not enough. Must say: "คัดลอกออกมาทั้งหมด ห้ามสรุป ห้ามตัด ห้ามอ้างอิงว่า 'ตามที่กล่าวข้างต้น' ต้องคัดลอกข้อความจริงออกมาทั้งหมด"

3. **google.genai SDK (v1.63.0) migration**: `result.embeddings[0].values` (not `result["embedding"]`). Multi-embed: `[e.values for e in result.embeddings]`.

4. **OAuth2 in Codespace**: OOB flow deprecated since 2022. Workaround: auth on local machine, copy `token.json` to Codespace. Or use Service Account (no browser needed).

5. **Gemini File API vs page-by-page**: Send whole PDF via File API — Gemini understands cross-page document structure. Vastly more accurate than PNG-per-page for Thai government legal documents.

---
*Added via Oracle Learn*
