---
title: ## Glossary Query Expansion, OCR Hallucination, and LLM Honesty
tags: [rag, hallucination, query-expansion, ocr, thai-legal-rag, debugging, honesty]
created: 2026-04-14
source: Oracle Learn
---

# ## Glossary Query Expansion, OCR Hallucination, and LLM Honesty

## Glossary Query Expansion, OCR Hallucination, and LLM Honesty

### Pattern: Glossary Expansion Cascades (per-query cap)
A query hitting multiple glossary keys simultaneously gets too many expansion terms. Fix: cap total glossary terms per query to 2-3 regardless of how many keys match. Prioritize longer/more-specific key matches.

### Pattern: stdout Buffering Masquerades as Hanging
`print("Loading...", end=" ")` gets buffered when output is redirected to a file. Process runs fine but output doesn't appear. Always run with `PYTHONUNBUFFERED=1` or `python3 -u` for background processes. Test with isolation before diagnosing deadlocks.
**Wrong theories first** (file locking → RAM exhaustion → Python no-GIL deadlock) before finding trivial root cause. Always test simplest hypothesis first.

### Pattern: OCR Summaries Are Invisible Hallucination Vectors
Gemini-generated `## บทสรุปสำหรับสืบค้น` sections can inject interpretive examples ("เช่น...") that aren't in the original document. These get indexed and retrieved as authoritative legal text.
**Most dangerous RAG failure mode**: hallucination baked into source data. No automated test catches it — only domain expert review.
**Fix**: Strengthen anchor prompt with anti-hallucination rules. Audit existing summaries.

### Pattern: Don't Name-Drop Tools Without Evidence
When discussing approaches, use generic descriptions ("Knowledge Graph approach") unless you can verify the specific tool is used in that domain. "LightRAG style" sounds authoritative but can be ungrounded. AI hallucination patterns are recursive — filling gaps with plausible-sounding specifics is the same whether it's LLM OCR summaries or assistant discussion.

### Pattern: Domain Experts Are the Best Hallucination Detectors
No automated eval catches "ลดวงเงิน isn't independent of เนื้องาน". Human domain expertise remains essential for RAG quality. Trust the human's challenge over the RAG's confident output — verify first, defend second.

---
*Added via Oracle Learn*
