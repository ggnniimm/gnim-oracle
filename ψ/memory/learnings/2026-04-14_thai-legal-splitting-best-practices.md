---
title: ## Thai Legal วรรค Splitting Best Practices
tags: [thai-law, วรรค, parsing, ocr, best-practices]
created: 2026-04-14
source: Thai Legal RAG 92→0 diffs 2026-02-21
---

# ## Thai Legal วรรค Splitting Best Practices

## Thai Legal วรรค Splitting Best Practices

วรรค = legal unit, not just a paragraph. Each วรรค has separate legal effect ("ตามวรรคหนึ่ง"). Numbered lists (๑)(๒)(๓) are WITHIN a วรรค, not new วรรค.

**Split signals** (new วรรค):
- "ในกรณีที่..." — almost always new วรรค
- "หลักเกณฑ์ วิธีการ..." — procedural wrap-up clause
- "องค์ประกอบ องค์ประชุม..." — committee sub-provision

**Do NOT split** (continuation words):
ทั้งนี้, ดังต่อไปนี้, โดย, เว้นแต่, ซึ่ง, อันได้แก่, ตาม, และให้, ดังนี้, ประกอบด้วย, จากนั้น, นับแต่

**OCR artifacts** to handle:
- Trailing topic heading: header of NEXT section bleeds into current → cut it
- Word wrap: mid-sentence line break ≠ new วรรค
- Blank lines: artifact ≠ paragraph break (unless multiple consecutive)
- Signature block: "ประกาศ ณ วันที่" → cut

**Fix strategy priority**: Rule-based trim → rule-based merge pass → Gemini semantic split → manual JSON cache patch → accept OCR gap

**Validation**: Compare against expert Excel reference. Run `--resplit` 3× — if diff count stable = framework robust.

---
*Added via Oracle Learn*
