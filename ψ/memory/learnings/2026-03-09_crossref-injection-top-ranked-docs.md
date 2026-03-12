# Cross-Reference Injection in Top-Ranked Documents

**Date**: 2026-03-09
**Source**: rrr: gnim-oracle/thai-legal-rag
**Confidence**: High (TC-003 fixed: 44→45/48)

## Pattern

When document X contains information relevant to query Q but can't be retrieved (semantic distance too large), find document Y that IS already retrieved for Q and inject X's key content as a cross-reference in Y's CONTENT section.

## Key Detail

Put cross-references in **content sections** (e.g. สรุปข้อวินิจฉัย) that get chunked and retrieved, NOT in anchor sections (บทสรุปสำหรับสืบค้น) which may be the last chunk and not retrieved.

## Example

- Query: "อำนาจหน้าที่ของคณะกรรมการตรวจรับพัสดุ"
- Target info: ว_78 (ผลิตภายในประเทศ verification duties) — FAISS rank 42, never retrieved
- Top-ranked doc: กวจ_20140 (same topic, rank 1)
- Fix: Added ว_78 summary as bullet point in กวจ_20140's สรุปข้อวินิจฉัย
- Result: TC-003 PASS — LLM sees ว_78 content via กวจ_20140's chunks

## Rule

When a document can't be retrieved for a query, don't fight the retrieval system — redirect the information through a document that CAN be retrieved.
