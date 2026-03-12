# ข้อเท็จจริง vs ข้อวินิจฉัย — Different Legal Weight

**Date**: 2026-03-07
**Source**: rrr: gnim-oracle
**Confidence**: high (corrected by domain expert)

## Pattern

Thai legal documents (ข้อหารือ กวจ, คำวินิจฉัย) have distinct sections with different authority:

| Section | Thai | Weight | Use as evidence? |
|---------|------|--------|-----------------|
| ข้อเท็จจริง | Background facts | Low | Context only, not ruling |
| ประเด็นข้อหารือ | Questions posed | Low | Framing only |
| ข้อวินิจฉัย | Actual ruling | High | Yes -- this is the authority |
| บทสรุปสำหรับสืบค้น | AI-generated summary | None | Derived, may contain errors |

## Trigger Case

ว126 had "(หัวหน้าหน่วยงานของรัฐ)" in ข้อเท็จจริง section as a parenthetical expanding "ผู้มีอำนาจ". The ข้อวินิจฉัย did NOT establish this -- it only said "หน่วยงานของรัฐสามารถใช้ดุลพินิจ..."

RAG retrieved the ข้อเท็จจริง text and the AI-generated summary, both of which contained the over-interpretation. The answer then confidently stated ผู้มีอำนาจ = หัวหน้าหน่วยงาน as if it were settled.

## Rule

When citing Thai legal documents:
1. Always identify which section the text comes from
2. Only use ข้อวินิจฉัย as authoritative evidence
3. ข้อเท็จจริง is context, not ruling
4. บทสรุปสำหรับสืบค้น is AI-generated -- may propagate interpretive errors

## Systemic Risk

AI-generated OCR summaries (บทสรุปสำหรับสืบค้น) inherit and amplify interpretive errors. One bad summary → indexed → retrieved → cited as authority → propagated to answers. Consider periodic audit of these sections.
