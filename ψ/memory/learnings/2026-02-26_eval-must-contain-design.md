# Eval must_contain: Read the LLM Output First

**Date**: 2026-02-26
**Source**: thai-legal-rag — eval suite TC-004 debugging
**Tags**: eval, must_contain, LLM-output, Thai-legal-phrases

---

## Pattern

When designing `must_contain` for LLM-based eval, **extract phrases from the actual LLM output**, not from what you think the answer should say. Thai legal phrases have qualifiers that break naive substring matching.

---

## Discovery

TC-004: "อำนาจในการแก้ไขสัญญาเป็นของใคร"

- **must_contain**: `"ผู้มีอำนาจสั่งซื้อ"` ← from memory of the legal concept
- **LLM output**: `"ผู้มีอำนาจ**อนุมัติ**สั่งซื้อหรือสั่งจ้าง"` ← from ว476 source text
- **Result**: substring match fails — "อนุมัติ" sits between "อำนาจ" and "สั่งซื้อ"

Fix: `"อนุมัติสั่งซื้อ"` — IS a substring of "ผู้มีอำนาจอนุมัติสั่งซื้อหรือสั่งจ้าง"

---

## Correct Workflow

```
1. Run the query through full pipeline (generate=True)
2. Read the FULL answer (not just 300-char snippet)
3. Find the phrase that expresses the key concept
4. Extract a substring that: (a) appears consistently, (b) is specific enough
5. Use that substring as must_contain
```

---

## Thai Legal Phrase Pitfalls

| Naive phrase | Actual LLM output | Fix |
|---|---|---|
| `ผู้มีอำนาจสั่งซื้อ` | `ผู้มีอำนาจอนุมัติสั่งซื้อหรือสั่งจ้าง` | `อนุมัติสั่งซื้อ` |
| `งดลดค่าปรับ` | `งดหรือลดค่าปรับ` | `ลดค่าปรับ` |
| `193` (มาตรา) | `วันทำการแรก` (concept) | `วันทำการ` |
| `103` (มาตรา) | `หัวหน้าหน่วยงาน` (concept) | `หัวหน้าหน่วยงาน` |

**Pattern**: LLM uses source document phrasing, not summary phrases. Article numbers are optional (LLM may cite them in a reference list or not at all).

---

## Secondary: Check Code Before Making Quality Claims

When user asked "ขาด --- มีผลต่อ RAG ไหม?" — correct answer came from reading `md_loader.py`, not from intuition. The code already had `_HYBRID_FRONTMATTER_RE` handling exactly this case.

**Rule**: Read the relevant code file before asserting whether a data formatting issue affects pipeline quality.
