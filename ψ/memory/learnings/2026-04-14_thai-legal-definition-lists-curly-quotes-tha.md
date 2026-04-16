---
title: ## Thai Legal Definition Lists — Curly Quotes
tags: [thai-law, regex, unicode, parsing, definition]
created: 2026-04-14
source: วรรค splitting — บทนิยาม sections 2026-02-18
---

# ## Thai Legal Definition Lists — Curly Quotes

## Thai Legal Definition Lists — Curly Quotes

Thai legal PDFs use Unicode curly quotes for definition terms, not ASCII:
- Opening: `"` = `\u201c` (LEFT DOUBLE QUOTATION MARK)
- Closing: `"` = `\u201d` (RIGHT DOUBLE QUOTATION MARK)

Format: `"การจัดซื้อจัดจ้าง" หมายความว่า ...`
Sometimes with parenthetical: `"ระบบข้อมูล" (Electronic Catalog : e-catalog) หมายความว่า ...`

```python
_DEFINITION_ITEM_RE = re.compile(
    r'^[\u201c"][^\u201d"]*[\u201d"].{0,60}?(หมายความว่า|หมายถึง|หมายรวมถึง)',
    re.UNICODE
)
```

**Debug tip**: When regex doesn't match text that looks identical visually, `print([hex(ord(c)) for c in text[:5]])` — `"` is `0x201c` not `0x22` (ASCII).

Only 2 sections have this pattern in Thai procurement law: มาตรา ๔ and ข้อ ๔ (บทนิยาม/definitions).

---
*Added via Oracle Learn*
