---
title: ## Cross-Reference Injection in Top-Ranked Documents
tags: [cross-reference, retrieval, rag, thai-legal, injection]
created: 2026-04-14
source: rrr: gnim-oracle/thai-legal-rag 2026-03-09
project: github.com/gnim-oracle/thai-legal-rag
---

# ## Cross-Reference Injection in Top-Ranked Documents

## Cross-Reference Injection in Top-Ranked Documents

When document X contains information relevant to query Q but can't be retrieved (semantic distance too large), find document Y that IS already retrieved for Q and inject X's key content as a cross-reference in Y's CONTENT section.

**Key detail**: Put cross-references in CONTENT sections (e.g. สรุปข้อวินิจฉัย) that get chunked and retrieved — NOT in anchor sections (บทสรุปสำหรับสืบค้น) which may be the last chunk and not retrieved.

**Example**: 
- Query: "อำนาจหน้าที่ของคณะกรรมการตรวจรับพัสดุ"
- Target info: ว_78 (FAISS rank 42, never retrieved)
- Top-ranked doc: กวจ_20140 (rank 1)
- Fix: Added ว_78 summary as bullet in กวจ_20140's สรุปข้อวินิจฉัย
- Result: TC-003 PASS

**Rule**: When a document can't be retrieved for a query, don't fight the retrieval system — redirect the information through a document that CAN be retrieved.

---
*Added via Oracle Learn*
