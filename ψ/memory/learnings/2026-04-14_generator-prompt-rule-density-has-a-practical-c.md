---
title: ## Generator Prompt Rule Density Has a Practical Ceiling
tags: [prompt-engineering, generator, rule-density, llm-behavior, gemini]
created: 2026-04-14
source: Thai Legal RAG TC-035/045 fix 2026-03-19
---

# ## Generator Prompt Rule Density Has a Practical Ceiling

## Generator Prompt Rule Density Has a Practical Ceiling

After ~10-12 rules in a system prompt, additional rules require increasingly specific/explicit language to be reliably followed by Gemini Flash.

**Evidence**: Rule 1 said "อ้างอิงข้อกฎหมาย/ระเบียบที่เกี่ยวข้องทุกครั้ง" (abstract). TC-035/045 consistently failed — LLM described มาตรา 103 content without citing "มาตรา 103" by number. Fix: explicit Rule 14 "ให้ระบุหมายเลขมาตราหรือข้อนั้นในคำตอบเสมอ — ห้ามอ้างเฉพาะชื่อ พ.ร.บ. โดยไม่ระบุมาตรา". Both TCs immediately PASS.

**Implication**:
- Abstract rules work for obvious cases, not edge cases
- Specific rules needed when model consistently misses a pattern
- At 14 rules, approaching practical ceiling — consolidate before adding more
- Each new rule competes for model's attention with existing rules

---
*Added via Oracle Learn*
