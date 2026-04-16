---
title: ## must_contain Stability: Use Source-Native Legal Terms
tags: [eval, must-contain, thai-legal, non-determinism, test-design]
created: 2026-04-14
source: Thai Legal RAG TC-013 + TC-014-023 design 2026-03-02
---

# ## must_contain Stability: Use Source-Native Legal Terms

## must_contain Stability: Use Source-Native Legal Terms

When designing must_contain for RAG eval, LLM phrasing is non-deterministic. Some terms are stable, others flaky.

**Stable** (use these):
- Established legal terms: "ประกาศเชิญชวนทั่วไป", "คัดเลือก", "เฉพาะเจาะจง"
- Fixed numbers: "500,000", "7 วัน", "3 วิธี"
- Terms directly quoted from source documents
- Broad action words: "ผ่อนปรน", "ค่าปรับ", "บอกเลิกสัญญา"

**Flaky** (avoid):
- Derived legal references: "มาตรา 102" when source uses "ข้อ 182"
- Specific phrasing variants: "แก้ไขเปลี่ยนแปลง" vs "แก้ไขสัญญา"
- Role titles that vary between specific case and general form

**Rule**: Use terms that appear directly in the source document text, not terms the LLM might derive or paraphrase.

**Pre vs Post-contract**:
- Post-contract (ตรวจรับ, แก้ไขสัญญา, ค่าปรับ): specific ข้อหารือ phrases
- Pre-contract (วิธีจัดซื้อ, วงเงิน, อุทธรณ์): broad statutory terminology (very stable)

---
*Added via Oracle Learn*
