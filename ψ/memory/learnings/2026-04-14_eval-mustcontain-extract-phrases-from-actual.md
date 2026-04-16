---
title: ## Eval must_contain: Extract Phrases from Actual LLM Output
tags: [eval, must-contain, thai-legal, substring-matching]
created: 2026-04-14
source: Thai Legal RAG eval TC-004 debugging 2026-02-26
---

# ## Eval must_contain: Extract Phrases from Actual LLM Output

## Eval must_contain: Extract Phrases from Actual LLM Output

When designing must_contain for eval, extract phrases from the ACTUAL LLM output — not from what you think the answer should say. Thai legal phrases have qualifiers that break naive substring matching.

**Example**:
- must_contain: `"ผู้มีอำนาจสั่งซื้อ"` (from memory)
- LLM output: `"ผู้มีอำนาจอนุมัติสั่งซื้อหรือสั่งจ้าง"` (from source text)
- Fix: `"อนุมัติสั่งซื้อ"` (IS a substring)

**Correct workflow**: Run query through full pipeline → read FULL answer → find phrase expressing key concept → extract substring that (a) appears consistently, (b) is specific enough.

**Common Thai legal patterns**:
- LLM uses source document phrasing, not summary phrases
- Article numbers are optional (LLM may cite in reference list or not at all)
- Avoid Thai numeral assertions — output is inconsistent between ๙๗ and 97

**Secondary rule**: Read the relevant code file before asserting whether a data formatting issue affects pipeline quality.

---
*Added via Oracle Learn*
