---
title: ## Retrieval Anchor Engineering + Eval Design Lessons (2026-02-26 to 2026-03-01)
tags: [retrieval-anchor, eval, must-contain, ocr, embedding-gap, thai-legal-rag, faiss, batch-reocr]
created: 2026-04-14
source: retro: 2026-02-26 to 2026-03-01 anchor + eval sessions
---

# ## Retrieval Anchor Engineering + Eval Design Lessons (2026-02-26 to 2026-03-01)

## Retrieval Anchor Engineering + Eval Design Lessons (2026-02-26 to 2026-03-01)

**Anchor sim floor constraint**: Anchor text needs minimum sim > ~0.78 to reach FAISS top-40. Even anchor at rank 1 (sim=0.9998) doesn't guarantee its keyword appears in LLM answer — if LLM has dense authoritative content from other sources, keyword headline gets overshadowed.

**Short anchor = retrieval win, sentence anchor = LLM synthesis**: These are mutually exclusive. Short keyword-dense anchor → retrieved, but LLM may not synthesize the keyword. Full sentence anchor → LLM synthesizes the content, but gets diluted by other vocabulary → sim drops below threshold. Both can't be optimized simultaneously.

**When anchor fails → create specific TC**: If a general TC can't stably include content X from document Y, create a specific TC where query is designed to make Y rank #1. Don't fight the embedding space.

**Thai numeral inconsistency in LLM output**: LLM uses Thai numerals "มาตรา ๙๗" and Arabic "มาตรา 97" interchangeably. must_contain should use the Arabic form or be flexible enough to handle both.

**Revert to backup immediately when sim drops**: If modifying MD content causes sim drop (0.8149 → 0.7659), revert MD + restore FAISS backup immediately before sleeping. Don't leave the index in a worse state overnight.

**Generic OCR prompt for attachments**: The structured ข้อหารือ OCR prompt skips attachments (สิ่งที่ส่งมาด้วย) — manuals, templates, wage tables. Use generic OCR prompt for batch re-OCR of low chars/page ratio files. chars/page ratio heuristic effectively flags incomplete OCR.

**Gemini refuses dense numerical tables**: Tables like wage grids may return 0 chars from Gemini OCR — known limitation. Flag as unrecoverable rather than retrying infinitely.

---
*Added via Oracle Learn*
