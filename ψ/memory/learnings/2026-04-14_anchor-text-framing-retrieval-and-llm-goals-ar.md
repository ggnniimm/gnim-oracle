---
title: ## Anchor Text Framing: Retrieval and LLM Goals Are Aligned
tags: [retrieval-anchor, embedding, llm-framing, rag]
created: 2026-04-14
source: Thai Legal RAG กวจ. 38381 fix 2026-02-26
---

# ## Anchor Text Framing: Retrieval and LLM Goals Are Aligned

## Anchor Text Framing: Retrieval and LLM Goals Are Aligned

When writing retrieval anchors, text structure affects BOTH embedding similarity AND LLM interpretation — and these goals are more aligned than they appear.

**Wrong structure** (LLM ignores items):
`คณะกรรมการ ไม่มีอำนาจสั่งการ ครอบคลุม: แก้ไขสัญญา ขยายระยะเวลา งดลดค่าปรับ บอกเลิกสัญญา`
→ LLM reads: constraint + footnote examples → summarizes to "ไม่มีอำนาจสั่งการ"

**Right structure** (LLM lists all):
`คณะกรรมการมีหน้าที่ 2 ประเภท: (1) ตรวจรับพัสดุ (2) เสนอความเห็น กรณีแก้ไขสัญญา ขยายระยะเวลา งดลดค่าปรับ บอกเลิกสัญญา (ไม่มีอำนาจสั่งการ)`
→ LLM enumerates all 4 cases ✓

Moving "ไม่มีอำนาจสั่งการ" from front to end also improved embedding similarity (0.8028 → 0.8136) because embedding models encode semantic frame — duty-first matches "มีหน้าที่อะไรบ้าง" better than constraint-first.

**Rules**: Lead with positive assertion. Use explicit enumeration structure "มี X ประเภท: (1)...(2)...". Put constraints at end as parentheticals. System prompt cannot override structure problems.

---
*Added via Oracle Learn*
