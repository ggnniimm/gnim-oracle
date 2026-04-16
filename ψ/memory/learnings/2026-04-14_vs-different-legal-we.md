---
title: ## ข้อเท็จจริง vs ข้อวินิจฉัย — Different Legal Weight
tags: [thai-legal, document-structure, rag, authority, data-quality]
created: 2026-04-14
source: rrr: gnim-oracle 2026-03-07
---

# ## ข้อเท็จจริง vs ข้อวินิจฉัย — Different Legal Weight

## ข้อเท็จจริง vs ข้อวินิจฉัย — Different Legal Weight

Thai legal documents (ข้อหารือ กวจ, คำวินิจฉัย) have sections with different authority:
- **ข้อเท็จจริง** — background facts, context only, NOT ruling
- **ประเด็นข้อหารือ** — questions posed, framing only
- **ข้อวินิจฉัย** — ACTUAL ruling, high authority, use as evidence
- **บทสรุปสำหรับสืบค้น** — AI-generated summary, may contain errors, no authority

**Trigger case**: ว126 had "(หัวหน้าหน่วยงานของรัฐ)" in ข้อเท็จจริง section as a parenthetical. RAG retrieved ข้อเท็จจริง text + AI summary, both containing the over-interpretation. Answer confidently stated ผู้มีอำนาจ = หัวหน้าหน่วยงาน as if settled law.

**Rule**: Only use ข้อวินิจฉัย as authoritative evidence.

**Systemic risk**: AI-generated OCR summaries inherit and amplify interpretive errors. One bad summary → indexed → retrieved → cited as authority → propagated. Periodic audit needed.

---
*Added via Oracle Learn*
