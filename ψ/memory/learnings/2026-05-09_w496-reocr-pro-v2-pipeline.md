# ว ๔๙๖ re-OCR with Pro v2 pipeline — fixing wrong-schema legacy MD

**Date**: 2026-05-09
**Source**: gnim-oracle/thai-legal-rag prod deploy
**Confidence**: High (real user impact verified — answer flipped from "ไม่มี" to correct form description)

## Trigger

User `00081698` asked on 2026-05-08 06:58:

> Q2: "ขอเเบบฟอร์มใช้เเจ้งปลัดกระทรวงการคลังเกี่ยวกับผู้ทิ้งงาน"

Got back this self-contradicting answer:

> "**ไม่มีแบบฟอร์มสำหรับแจ้งปลัดกระทรวงการคลังเกี่ยวกับผู้ทิ้งงานแนบมาโดยตรง** [1]...[14]
> อย่างไรก็ตาม เอกสารอ้างอิงระบุว่า: คณะกรรมการวินิจฉัยฯ ได้กำหนด 'แบบแจ้งผู้ทิ้งงาน' ขึ้น... [เลขที่ ว 496]"

The answer **cited ว ๔๙๖** in the body but **led with "ไม่มี"** — confusing for the user. ว ๔๙๖ IS in prod (12 chunks at the time, file_id `1nzNwP7uFYKAM9zbgIEa81RtJ404Oh3Wp`).

## Root cause: wrong-schema legacy OCR

`แบบแจ้งผู้ทิ้งงาน.md` was OCR'd 2026-02-23 with `gemini-2.0-flash` **before** today's pipeline refactor that introduced doc-type-aware section schemas + filename-safety-net. The classifier mis-routed it to **`Ruling_Committee`** schema (with `## ข้อเท็จจริง`/`## ข้อวินิจฉัย`) instead of **`Circular`** (with `## หลักการและที่มา`/`## แนวปฏิบัติ`/`## การใช้บังคับ`/`## ข้อสังเกต`).

Consequence: the actual form body — Pages 2–9 of the PDF with checkboxes for มาตรา ๑๐๙ (๑)–(๖), data fields (ชื่อบุคคล / เลขทะเบียน / ภูมิลำเนา / สาเหตุ), ภาคผนวก ก–ข — fell outside the Ruling schema's expected sections and was lost. The MD was just the cover-letter announcement that "the form exists", not the form itself. So the LLM correctly said "ไม่มีฟอร์มแนบโดยตรง" (no form attached *to its retrieved context*) — that disclaimer was accurate-given-context but misleading because the underlying corpus wasn't representing the document correctly.

The filename-safety-net (`_ว\d` regex) doesn't fire on `แบบแจ้งผู้ทิ้งงาน.pdf` either — it relies on the `ว` being in the underscore-separated filename pattern. So the only way to get correct routing on this file was via a rerun of the post-refactor classifier.

## Fix

Re-OCR with the new Pro v2 pipeline (Flash classify → Pro extract → Flash anchor):

```python
from src.ingestion.drive import stream_pdf
from src.ingestion.ocr import pdf_to_markdown

pdf_bytes = stream_pdf("1nzNwP7uFYKAM9zbgIEa81RtJ404Oh3Wp")
result = pdf_to_markdown(pdf_bytes, file_id=..., filename=..., force=True)
```

Pipeline did exactly what it was designed for:

- Flash classifier: 100% Circular ✓ (post-refactor classifier prompt has explicit Circular criteria)
- Pro extract: caught the form body — `### แบบแจ้งผู้ทิ้งงาน (แบบ ทง.)` with all 6 checkbox items, plus `### ภาคผนวก ก` and `### ภาคผนวก ข`
- Flash anchor: 429-throttled on first try (non-fatal); regen succeeded ~12 min later

Then scp → prod → force-reindex.

## Schema comparison (ว ๔๙๖, before vs after)

| Aspect | Old Flash MD (2026-02-23) | New Pro v2 MD (2026-05-09) |
|---|---|---|
| Schema | Ruling_Committee | **Circular** ✓ |
| ocr_engine | gemini-2.0-flash | gemini-2.5-pro |
| Sections | `## ข้อเท็จจริง` (wrong) | `## หลักการและที่มา` / `## แนวปฏิบัติ` / `## การใช้บังคับ` / `## ข้อสังเกต` |
| Form body | Missing | Present (line 33–240, with checkboxes + appendices) |
| doc_number | "เลขที่ ว ๔๙๖" (partial) | "ที่ กค (กวจ) ๐๔๐๕.๒/ว ๔๙๖" (full) |
| laws_referenced | 4 entries | 9 entries (incl. มาตรา ๑๐๙ (๑)–(๖) + ม.๒๔(๖) + ม.๒๙(๓) + ระเบียบ ข้อ ๑๙๓) |
| MD size | 7,937 bytes | 13,461 bytes (+anchor) |
| Prod chunks | 12 | 44 |

## Verification

### Same query (typo `เเ` exactly as user typed)

| Run | ว ๔๙๖ rank |
|---|---|
| Pre re-OCR | #8 |
| Post Pro v2 (no anchor) | **#4** ↑ |
| Post Pro v2 + anchor | **#4** (anchor didn't change rank — known: anchor chunks rarely top-K) |

### LLM answer change (full generator pipeline, prod)

**Before**: opens with "ไม่มีแบบฟอร์มสำหรับแจ้งปลัดกระทรวงการคลังเกี่ยวกับผู้ทิ้งงานแนบมาโดยตรง [1]...[14] อย่างไรก็ตาม..."

**After**: opens with "**1. แบบฟอร์มใช้แจ้งปลัดกระทรวงการคลังเกี่ยวกับผู้ทิ้งงาน** มี 'แบบแจ้งผู้ทิ้งงาน' ที่คณะกรรมการวินิจฉัยฯ กำหนดขึ้น... แบบแจ้งผู้ทิ้งงานดังกล่าวจะระบุข้อมูลทั่วไป เช่น ชื่อบุคคล/ชื่อนิติบุคคล, เลขที่ทะเบียนพาณิชย์/เลขที่ทะเบียนนิติบุคคล, ภูมิลำเนา/สำนักงานที่ตั้ง... โดยให้ทำเครื่องหมาย X ในช่องสาเหตุของการพิจารณาเป็นผู้ทิ้งงาน [4]"

The "ไม่มี" disclaimer is gone — replaced with concrete form-field details extracted from the PDF that Pro v2 finally captured. **Real user-facing fix.**

## Backup

- Prod backup: `/tmp/prod_backups/w496.prod_backup_2026-05-09.md` (7.9 KB Flash old)

## Pending follow-up

- **Corrected-typo variant regression**: query `ขอแบบฟอร์มใช้แจ้งปลัดกระทรวงการคลัง...` (without `เเ` typo) ranks ว ๔๙๖ NOT-in-top-30. The user's typo version goes to #4. Stable across 3 runs. Not a blocker since user pre-typed the typo, but odd. Hypothesis: chunk count went 12 → 44, may dilute file_id representation for some phrasings while concentrating it for others. Worth diagnosing if more Q-class issues surface.
- **Other legacy `gemini-2.0-flash` MDs**: this one was found by tracing a real user complaint. There may be more in the corpus where wrong-schema OCR is silently degrading answers. Worth a corpus-level grep `ocr_engine: "gemini-2.0-flash"` to see how many candidates exist.

## Reusable lesson (for the lessons file)

When a user's answer is self-contradictory ("X is missing... however X exists per [doc]"), the doc IS retrieving but its MD body doesn't contain the answer's specifics. Often that means the OCR captured only the cover/announcement layer of a multi-page PDF, missing the actual content (forms, attachments, appendices). Re-OCR with the doc-type-aware pipeline often fixes it without any prompt or retrieval changes.

## Related

- `2026-05-09_w210-q2-crossref-injection.md` — sibling fix on a different ว document (cross-ref injection there, re-OCR here)
- `2026-05-09_pro-vs-flash-ocr-verbatim-tradeoff.md` — broader context on Pro v2 prompt rules
- `2026-04-30_corpus-resync-and-tc044-tc050-fixes.md` — corpus-level resync that established this repo as canonical
