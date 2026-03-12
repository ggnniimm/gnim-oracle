# Glossary Expansion Can Cause Regression

**Date**: 2026-03-10
**Source**: rrr: gnim-oracle/thai-legal-rag
**Confidence**: High (confirmed TC-025 regression)

## Pattern

Adding terms to glossary expansion improves target TC but can break unrelated TCs that share the same trigger keyword.

## Example

Added "ว ๑๐๘" + "แนวทางปฏิบัติการดำเนินการภายหลัง" to `บอกเลิกสัญญา` glossary entry.
- TC-042: ว108 jumped from rank 129 → rank 5 (great!)
- TC-025 ("การจ้างช่วง"): FAIL — query contains "บอกเลิกสัญญา" somewhere, got polluted with irrelevant ว108 chunks

## Rule

Before adding glossary terms:
1. Check how many queries in eval contain the trigger keyword
2. Run targeted eval on those queries BEFORE full eval
3. Prefer narrow triggers (multi-word phrases) over broad single keywords

## Also Learned

CHUNK_SIZE=400 splits bullet lists. If a key phrase is in the last bullet of สรุปข้อวินิจฉัย, it may end up in a separate chunk that doesn't get reranked into top-K. Fix: move critical phrases to early bullets (within first 400 chars).
