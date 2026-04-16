---
title: ## Thai Legal RAG — Lessons Learned from Early POC (thai-rag-poc)
tags: [thai-legal-rag, lessons-learned, architecture, poc, ocr, deduplication, eval, lightrag]
created: 2026-04-14
source: thai-legal-rag-lessons.md — 2026-02-13
---

# ## Thai Legal RAG — Lessons Learned from Early POC (thai-rag-poc)

## Thai Legal RAG — Lessons Learned from Early POC (thai-rag-poc)

From `ggnniimm/thai-rag-poc` (Jan–Feb 2026) running 700+ real documents from กรมบัญชีกลาง, ศาลปกครอง, สำนักงานอัยการสูงสุด.

**What works**:
- Gemini embedding-004 (3072 dim) — good quality, free quota for batch index
- LightRAG (graph-based) — good for multi-document reasoning
- PyThaiNLP `sent_tokenize` — correct chunking, prevents mid-sentence cuts
- Gemini 2.0 Flash — cheap and fast for answer generation
- Query Expansion — creates Thai keywords from questions, helps recall significantly
- Persona "นิติกรชำนาญการพิเศษ" in system prompt → correct answer style

**Mistakes to avoid**:
1. **Flat file structure kills itself**: batch_add_* scripts accumulate → can't tell which is canonical. Fix: proper module structure with single canonical CLI script.
2. **FAISS + LightRAG not fused**: UI forced user to choose mode. Should: query both → rerank → merge → send to LLM.
3. **No deduplication → index repeats**: Generates check_faiss_count.py, find_missing_*.py, recover_*.py spirals. Fix: content hash before indexing.
4. **Tesseract Thai OCR fails**: Government scan PDFs → skewed text → Tesseract fails. Fix: send PDF pages as images directly to Gemini Vision.
5. **Hardcoded local paths**: Breaks on other machines. Fix: centralized config, no hardcoded paths.
6. **No evaluation**: "Tested and answered correctly" isn't systematic eval. Fix: build eval suite with must_contain criteria.

**Clean Architecture**: `src/{ingestion,indexing,retrieval,generation,config}` + `pipeline/` (thin CLI wrappers) + `app/streamlit_app.py` + `tests/`.

---
*Added via Oracle Learn*
