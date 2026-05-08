---
name: Thai Procurement Law — Temporal Split in Contract Amendment Rules
description: Before-signing vs after-signing contract term changes have different legal paths
type: learning
concepts: ["procurement-law", "contract-amendment", "thai-legal", "temporal-rules", "ม.97"]
source: "rrr: gnim-oracle (2026-05-06 session + กวจ 3061 + กวจ 30307)"
date: 2026-05-06
status: SUPERSEDED
superseded_by: 2026-05-07_thai-exemption-rulings-non-transferable.md
superseded_reason: Overgeneralized from กวจ 30307 (an exemption case, non-transferable) into a "before/after signing" rule. Ming corrected 2026-05-07.
---

> ⚠️ **SUPERSEDED 2026-05-07** — see `2026-05-07_thai-exemption-rulings-non-transferable.md`. The "before signing = flexible" framing below is **wrong**: กวจ 30307 was a specific exemption granted to one agency, not a general pathway. Each agency must request its own exemption case-by-case. Kept for reference only.

---

# Thai Procurement Law — Temporal Split in Contract Amendment Rules

## The Pattern

Thai procurement law (พ.ร.บ.จัดซื้อจัดจ้างฯ พ.ศ. 2560) treats contract term changes differently depending on **when** the request is made:

### BEFORE Signing (ก่อนลงนาม)
**Status**: ✅ Flexible  
**Rule**: เอกสารประกวดราคา (procurement documents) can be changed if state benefits  
**Example**: Contractor requests NOT to receive advance payment → change bid docs → **no contract amendment needed**  
**Source**: กวจ 30307 (2021-07-08)
**Key quote**: "ระเบียบฯ มิได้กำหนดให้ห้าม..." (rules don't forbid changes if state benefits)

### AFTER Signing (หลังลงนาม)
**Status**: ❌ Locked  
**Rule**: มาตรา 97 วรรค 1 — "สัญญาจะแก้ไขไม่ได้ เว้นแต่..."  
**Exceptions** (must be case-by-case):
1. ตาม มาตรา 93 วรรค 5 (specific situations)
2. ไม่ทำให้หน่วยงานของรัฐ เสียประโยชน์ (no state loss)
3. เป็นประโยชน์แก่หน่วยงานของรัฐ (state benefit)
4. กรณีอื่น ตามกฎกระทรวง (other regulatory cases)

**Example**: Change fixed-price contract to adjustable (K value) → invoke มาตรา 97 exception → requires ministerial approval if complex  
**Source**: กวจ 3061 (2024-01-24)

---

## Why This Matters

| Scenario | Path | Effort |
|----------|------|--------|
| Contractor waives advance payment **before signing** | Change bid docs, no amendment | ✅ Easy |
| Contractor waives advance payment **after signing** | Submit amendment to ministry for exemption review | ⚠️ Hard |
| Change fixed contract to price-adjusted **before signing** | Include in bid docs | ✅ Easy |
| Change fixed contract to price-adjusted **after signing** | Invoke มาตรา 97 exception, ministry sign-off | ⚠️ Hard |

**Implication**: Time of request = complexity of solution.

---

## Ming's Question (2026-05-06)

**Q**: "ผู้รับจ้างไม่เบิกเงินล่วงหน้า ต้องแก้ไขสัญญาหรือไม่?"  
(If contractor doesn't claim advance payment, must contract be amended?)

**A**: Depends on timing:
- **Before signing**: No amendment needed (change bid docs)
- **After signing**: Amendment needed (invoke exception)

---

## How to Apply

When analyzing procurement contract disputes:
1. **Check the timestamp**: When was the change requested?
2. **If before signing**: Easier path (change procurement docs)
3. **If after signing**: Harder path (exemption + ministerial review)
4. **If uncertain**: Use pre-signing path when possible (cost-benefit for state)

---

## Related Documents

- **กวจ 3061**: Contract amendment after signing (fixed → price-adjusted)
  - File: `ψ/lab/thai-legal-rag/data/md_backup/01_กวจ_3061_240167_...md`
  - Date: 2024-01-24

- **กวจ 30307**: Advance payment waiver before signing (accepted as exemption)
  - File: `ψ/lab/thai-legal-rag/data/md_backup/01_กวจ_30307_080764_...md`
  - Date: 2021-07-08

---

## Tags

`#procurement-law` `#contract-amendment` `#thai-legal` `#temporal-rules` `#ม.97` `#mingq`
