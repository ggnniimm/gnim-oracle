---
title: ## Definitional TC must_contain — Use Concept Words
tags: [eval, must-contain, definitional, thai-legal, llm-variance]
created: 2026-04-14
source: Thai Legal RAG TC design 2026-03-15
---

# ## Definitional TC must_contain — Use Concept Words

## Definitional TC must_contain — Use Concept Words

For "คืออะไร" type TCs (definitional questions), LLM variance is high because LLM can answer in many ways.

**Rule**: must_contain for definitional TC should use high-semantic concept words that appear in EVERY good answer — e.g., "ความระมัดระวัง", "ชดใช้", "ละเมิด" — NOT specific legal phrases like "จงใจ" or "มาตรา 8" which the LLM may choose not to mention.

**Why**: TC-065 "ประมาทเลินเล่อย่างร้ายแรง คืออะไร" required 3 runs — must_contain "จงใจ" failed, "ชดใช้" failed second time.

**How to apply**: Before setting must_contain, ask "Will EVERY good answer always contain this word?" If unsure, choose a broader word, or run query 2-3 times first to see which words are stable.

---
*Added via Oracle Learn*
