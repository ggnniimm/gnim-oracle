---
title: ## Cross-Reference Extraction in Thai Law (2026-02-16)
tags: [thai-legal, cross-reference, regex, graph, procurement-law, backwards-compatibility]
created: 2026-04-14
source: retro: 2026-02-16 cross-reference-extraction
---

# ## Cross-Reference Extraction in Thai Law (2026-02-16)

## Cross-Reference Extraction in Thai Law (2026-02-16)

**Thai legal cross-references follow highly regular patterns**: `มาตรา\s+[๐-๙]+` regex covers all cases. Thai legal text has consistent formatting — regex is the right tool, no LLM needed.

**Keyword classification by proximity (lookbehind/lookahead)**: Look back 30 chars from the reference for keyword type:
- `ภายใต้บังคับ` → subordinate_to
- `ตาม`, `แห่ง` → reference
- `แก้ไข`, `เพิ่มเติม` → amended_by

**Backwards-compatible cache handling**: When adding fields to existing data structures, use `setdefault("references", [])` in both write and read paths. Old cache files gracefully degrade.

**Plan estimates ≠ test assertions**: Estimates written from memory (without reading actual legal text) were wrong (expected ข้อ 55 = ~8 วรรค, actual = 5). Approximate direction is fine, but treat code output as ground truth, not the plan.

**169/365 sections had cross-references**: About half of procurement law sections reference other sections — dense web of legal dependencies. Graph visualization would reveal which sections are most central.

---
*Added via Oracle Learn*
