# Thai Legal Definition Lists — Curly Quotes & หมายความว่า

**Date**: 2026-02-18
**Context**: วรรค splitting — บทนิยาม sections (มาตรา/ข้อ 4)

## Pattern

Thai legal PDFs use Unicode curly quotes for definition terms, not ASCII:
- Opening: `"` = `\u201c` (LEFT DOUBLE QUOTATION MARK)
- Closing: `"` = `\u201d` (RIGHT DOUBLE QUOTATION MARK)

Definition items look like: `"การจัดซื้อจัดจ้าง" หมายความว่า ...`

Sometimes there's a parenthetical between the closing quote and หมายความว่า:
`"ระบบข้อมูลสินค้า" (Electronic Catalog : e-catalog) หมายความว่า ...`

## Fix

```python
_DEFINITION_ITEM_RE = re.compile(
    r'^[\u201c"][^\u201d"]*[\u201d"].{0,60}?(หมายความว่า|หมายถึง|หมายรวมถึง)',
    re.UNICODE
)
```

- Handles both ASCII `"` and curly `\u201c\u201d` quotes
- `.{0,60}?` allows optional content between closing quote and หมายความว่า
- Treat matched paragraphs as list items → merge into previous, enter list context

## Debug Tip

When regex doesn't match text that looks identical visually:
```python
print([hex(ord(c)) for c in text[:5]])
# "การ..." → ['0x201c', '0xe01', '0xe32', '0xe23', ...]
# Not 0x22 (ASCII ") — it's 0x201c (curly quote)
```

## Scope

In พ.ร.บ.จัดซื้อจัดจ้างฯ 2560 + ระเบียบฯ จัดซื้อจัดจ้าง 2560:
- Only 2 sections have this pattern: มาตรา ๔ and ข้อ ๔ (บทนิยาม/definitions)
- Result: 21→1 and 4→1 วรรค respectively
