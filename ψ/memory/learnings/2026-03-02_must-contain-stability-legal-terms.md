# must_contain Stability: Use Source-Native Legal Terms

**Date**: 2026-03-02
**Source**: thai-legal-rag TC-013 flake + TC-014-023 design
**Tags**: eval, must_contain, LLM-non-determinism, legal-terminology, test-design

## Pattern

When designing must_contain for RAG eval test cases, the LLM's phrasing is non-deterministic. Some terms are stable, others are flaky.

## Stable vs Flaky Terms

**Stable** (use these):
- Established legal terms: "ประกาศเชิญชวนทั่วไป", "คัดเลือก", "เฉพาะเจาะจง"
- Fixed numbers: "500,000", "7 วัน", "3 วิธี"
- Terms directly quoted from source documents
- Broad action words: "ผ่อนปรน", "ค่าปรับ", "บอกเลิกสัญญา"

**Flaky** (avoid these):
- Derived legal references: "มาตรา 102" when the source uses "ข้อ 182" (ระเบียบ reference vs พ.ร.บ. reference)
- Specific phrasing variants: "แก้ไขเปลี่ยนแปลง" vs "แก้ไขสัญญา"
- Role titles that vary: "ผู้อำนวยการองค์การ..." (specific case) vs "หัวหน้าหน่วยงานของรัฐ" (general)

## Rule of Thumb

Use terms that appear *directly in the source document's text*, not terms the LLM might derive or paraphrase. If the source ข้อหารือ discusses "ข้อ 182 ของระเบียบ", use "ข้อ 182" not "มาตรา 102 ของ พ.ร.บ." — even though they refer to the same legal principle.

## Pre-Contract vs Post-Contract Topics

- **Post-contract** topics (ตรวจรับ, แก้ไขสัญญา, ค่าปรับ): Pull from specific ข้อหารือ → must_contain should use ข้อหารือ-specific phrases
- **Pre-contract** topics (วิธีจัดซื้อ, วงเงิน, อุทธรณ์): Pull from broad พ.ร.บ./ระเบียบ/กฎกระทรวง → must_contain should use established statutory terminology (very stable)
