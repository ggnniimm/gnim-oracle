---
title: ## Batch Gemini Anchor Generation
tags: [gemini, retrieval-anchor, batch-processing, thai-legal]
created: 2026-04-14
source: Thai Legal RAG auto-anchor feature 2026-03-01
---

# ## Batch Gemini Anchor Generation

## Batch Gemini Anchor Generation

When generating keyword-dense retrieval summaries for hundreds of documents:
1. Use simple constrained prompt: "N keywords + M sentences, plain text only"
2. Truncate input to ~4000 chars (enough context, avoids token waste)
3. Rate limit at 1 req/sec for free-tier Gemini
4. Make idempotent: check if output section already exists before processing
5. Build retry into workflow

**Prompt that works**:
```
คำสำคัญ 15-20 คำ + สรุป 2-3 ประโยค
ห้ามใส่หัวข้อ ห้ามใส่ bullet ให้เขียนเป็น plain text เท่านั้น
```
"plain text only" prevents Gemini from adding markdown formatting that creates noisy chunks.

**Key numbers**: 970 files in ~52 minutes (3.5 sec/file), 99.8% success rate, 2,163 new chunks (~2.2 per file), zero eval regressions.

---
*Added via Oracle Learn*
