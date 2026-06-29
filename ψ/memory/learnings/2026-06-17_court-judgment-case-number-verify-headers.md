---
date: 2026-06-17
type: learning
topic: thai-legal-rag / OCR / court-judgment ingestion
---

# Verify court-judgment เลขคดีแดง against high-res headers — never trust OCR or auto-naming

## Context
Ming added 4 scanned คำพิพากษาศาลปกครองสูงสุด PDFs (downloaded from the court site,
strange filenames, no text layer) to ingest into the RAG corpus. Ran the full local
pipeline: `ocr_v4.py` → structure → name `ref_sac_o_<num>_<year>.md` → index → BM25 → verify.

## The trap
Both the 300 DPI Gemini-2.5-Pro verbatim OCR **and** `ocr_v4.py`'s auto-namer misread the
Thai-digit เลขคดีแดง (red case number) on 2 of 4 files:
- `๗๑๓/๒๕๖๘` → OCR read `๒๔๓/๒๕๖๔`  (auto-named `o_243_2564`)
- `๑๒๕๒/๒๕๖๘` → OCR read `๑๒๘๒/๒๕๖๗`  (auto-named `o_1282_2567`)

The red case number is the **canonical filename + doc_number**, so a misread silently
mislabels the document.

## The tell that caught it
A judgment's เลขคดีแดง **year must equal the judgment year** (the วันที่...พุทธศักราช line).
Both bad reads had red-number years (2564, 2567) earlier than both the judgment date (2568)
and the black case number's filing year (2566) — logically impossible. That inconsistency
is the cheap automated flag: `red_year == judgment_year`, else re-verify.

## Fix workflow
1. Render the header region at 360–700 DPI (`fitz` clip on top ~25%, right ~65%) and read
   the digits by eye. Thai ๒/๖, ๕/๘, ๘/๙, ๗/๒ confuse constantly.
2. Correct the เลขคดีแดง line in the verbatim `_ocr_v4.md` **before** structuring, so the
   extracted `doc_number`/`date_be` come out right.
3. Keep `doc_number` in **Thai numerals** (corpus convention) — Gemini sometimes emits Arabic.

## Pipeline notes (local PDFs not yet on Drive)
- `extract_ac_judgments.py` can't run as-is: it pulls verbatim MD + PDF from Drive AC folders.
  Wrote `pipeline/structure_local_judgments.py` — reuses its `EXTRACT_PROMPT` against a local
  `_ocr_v4.md`, `file_id` placeholder patchable later.
- Court-judgment PDFs live in Drive folder **AC = `1_NGGLSfMmlaICUNLXZym6MrCfJiWyRfI`**
  (the `FOLDER_AC_PDF` constant in `extract_ac_judgments.py` is stale → 404). Upload there,
  capture file_id, patch frontmatter `file_id`/`file_url`, then index.
- `index_md_folder.py` does **not** touch BM25. Always run `rebuild_bm25_from_qdrant.py` after
  (it rebuilds 1:1 from Qdrant — never append, which corrupts; see [[bm25-corruption-and-id-query-rerank]]).
- Local Qdrant is double-indexed (BM25 rebuild reported 2604 dup signatures) — local retrieval
  is fine to confirm *presence*, but eval correctness must be replayed on prod.
- `pipeline/query.py` is currently broken (imports removed `VECTOR_BACKEND` from config) —
  verify retrieval via `Retriever` + `rerank` directly instead.

## Result
4 judgments indexed local (Qdrant 34,212 → 34,271, +59 chunks), BM25 rebuilt
(34,271 == 34,271 MATCH), each retrievable at rank #1 for its targeted query.

| file | เลขคดีแดง | date | parties |
|------|----------|------|---------|
| ref_sac_o_9_2568    | อ.๙/๒๕๖๘    | 6 ม.ค. 68  | บ.ผลธัญญะ ↔ ทต.ออนใต้ |
| ref_sac_o_476_2568  | อ.๔๗๖/๒๕๖๘  | 30 มิ.ย. 68 | หจก.ภักสุธีโกศล ↔ ทต.กะรน |
| ref_sac_o_713_2568  | อ.๗๑๓/๒๕๖๘  | 25 ส.ค. 68  | บ.ผลธัญญะ ↔ ทต.ม่วงยาย |
| ref_sac_o_1252_2568 | อ.๑๒๕๒/๒๕๖๘ | 3 ธ.ค. 68   | อบต.ละเอาะ ↔ หจก.เค.เอส.บี |

Pending finalization: prod deploy (SCP + index + rebuild BM25 on prod), optional Drive
md_backup copy, git commit.
