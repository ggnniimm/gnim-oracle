# ว210 cross-ref injection — Q2 "มีผลบังคับใช้เมื่อใด" fix

**Date**: 2026-05-09
**Source**: gnim-oracle/thai-legal-rag prod deploy
**Confidence**: High (4/4 spot queries PASS post-fix)

## Problem

After Pro v2 OCR re-deploy of ว ๒๑๐ (37 chunks, down from 120 KB Flash version's many chunks), spot query Q2 dropped from #8 (already weak) to NOT-in-top-10:

> Q2: "การยกเว้นข้อ 46 47 52 มีผลบังคับใช้เมื่อใด"

Top-3 went to ว ๒๖๐ + ๒ อื่น — those also reference ข้อ 46/47/52 and outranked ว ๒๑๐ semantically.

## Root cause

ว ๒๑๐'s answer to Q2 spans **two chunks**:

- `## หลักการและที่มา` (chunk #1–9): contains "ข้อ ๔๖ ข้อ ๔๗ และข้อ ๕๒" (in ratio decidendi sentence)
- `## การใช้บังคับ` (chunk near end): contains "มีผลใช้บังคับตั้งแต่วันที่ ๕ พฤษภาคม ๒๕๖๙"

CHUNK_SIZE=400 → keyword set "ข้อ 46/47/52" + "มีผลบังคับใช้" never co-occur in a single chunk. Reranker can't find a single chunk that semantically matches both halves of the query.

## Fix

Prepended one synthesis bullet at the top of `## การใช้บังคับ` (line 73 of MD), pairing keyword and date in one sentence + dual numeral systems for retrieval surface:

```markdown
**สรุปการบังคับใช้**: การยกเว้นข้อ ๔๖ ข้อ ๔๗ และข้อ ๕๒ (ข้อ 46 ข้อ 47 และข้อ 52)
ตามหนังสือเวียน ว ๒๑๐ ฉบับนี้ มีผลใช้บังคับตั้งแต่วันที่ ๕ พฤษภาคม ๒๕๖๙
(5 พฤษภาคม 2569) เป็นต้นไป
```

True synthesis (no invented info) — both facts are stated separately in source. The bullet lives in a CONTENT section (per `2026-03-09_crossref-injection-top-ranked-docs.md` rule, NOT in anchor).

## Verification (prod, 4 spot queries from 2026-05-08 handoff)

| Query | Pre-fix | Post-fix |
|---|---|---|
| ว 210 รับฟังความคิดเห็น | #1 | **#1** |
| การยกเว้นข้อ 46 47 52 มีผลบังคับใช้เมื่อใด | NOT in top-10 | **#1** ↑ |
| ผู้ประกอบการสอบถามรายละเอียด | #1 | **#1** |
| หนังสือเวียน ว 210 บังคับใช้ตั้งแต่วันที่ | #1 | **#1** |

4/4 PASS post-fix.

## Deploy

- File: `ψ/lab/thai-legal-rag/data/md_backup/01_กวจ_ว210_240369_การอนุมัติยกเว้นการปฏิบัติตามระเบียบฯ+ข้อ+46+ข้อ+47+และข้อ+52.md`
- file_id: `1NixH_IpSQVB5PwEdOfzc7Xd1l3Z6uYZp`
- scp local → prod, force-reindex via `pipeline/index_md_folder.py --force-reindex --file <name> --no-lightrag`
- Reindex: deleted 37 vectors, indexed 37 new chunks (45s). Total prod 28,705 → 28,742.

## Risk to watch

The injection bullet is NOT in the source PDF — it's a RAG-optimization synthesis in the MD. **A future re-OCR of ว ๒๑๐ will overwrite this MD and lose the injection.** Two ways this can happen:
1. `pdf_to_markdown(force=True)` rerun — overwrites md_backup file
2. Batch re-OCR of all circulars

Mitigation: this file's `quality_note` field could flag the injection (e.g. `"manual cross-ref bullet at line 73 — preserve on re-OCR"`), or maintain a registry of injected docs in a separate file. Not done in this fix — TODO if Q2-class regressions recur after future re-OCR.

## Related learnings

- `2026-03-09_crossref-injection-top-ranked-docs.md` — original cross-ref pattern
- `2026-03-11_crossref-target-top-ranked-doc.md` — must target #1-ranked doc
- This case: target is the doc itself (we want IT to rank for Q2), not a competitor
