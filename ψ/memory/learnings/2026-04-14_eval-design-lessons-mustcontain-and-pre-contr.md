---
title: ## Eval Design Lessons: must_contain and Pre-Contract Topics
tags: [eval, must_contain, thai-legal-rag, procurement-law, test-design]
created: 2026-04-14
source: Oracle Learn
---

# ## Eval Design Lessons: must_contain and Pre-Contract Topics

## Eval Design Lessons: must_contain and Pre-Contract Topics

### Context
Thai Legal RAG evaluation suite — TC-013 through TC-023 covering pre-contract signing phase.

### Pattern: must_contain Should Use Source Document's Own Phrasing
When `must_contain` fails, prefer terms that appear directly in the source document's text, not derived legal references.

Example: Document 5529 uses ข้อ 182/183 of ระเบียบ to implement มาตรา 102 of พ.ร.บ. The LLM may cite either one. Use the ระเบียบ reference if the source is ระเบียบ-based. `"บอกเลิกสัญญา"` is more stable than `"มาตรา 102"` when the source document doesn't use that exact term.

### Pattern: Pre-Contract Topics Use Stable Legal Terminology
Pre-contract topics (วิธีจัดซื้อ, วงเงิน, อุทธรณ์) pull from broad legal sources (พ.ร.บ., ระเบียบ, กฎกระทรวง) → must_contain should use established legal terminology: "ประกาศเชิญชวนทั่วไป", "คัดเลือก", "เฉพาะเจาะจง", numeric thresholds like "500,000", time periods like "7 วัน". These are fixed in law and stable across LLM runs.

### Pattern: Use Eval Runner, Not Inline Scripts
`run_eval.py` handles `sys.path.insert` and `IndexManager(use_lightrag=False)` correctly. Inline Python scripts hit import errors. Always use the eval runner for queries that need the full retrieval pipeline.

### Pattern: Context Overflow Resumption Tax
After context overflow, re-discovery of imports, paths, and configurations costs 5-10 minutes. Keep a session handoff note with exact commands and file paths for resumption.

---
*Added via Oracle Learn*
