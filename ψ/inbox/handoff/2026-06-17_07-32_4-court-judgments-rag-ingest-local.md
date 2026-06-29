# Handoff: Ingest 4 ศาลปกครองสูงสุด judgments into RAG (local done, prod pending)

**Date**: 2026-06-17 07:32
📡 Session: 872bd051 | gnim-oracle | thai-legal-rag corpus add

## Context
Ming dropped 4 scanned คำพิพากษาศาลปกครองสูงสุด PDFs (strange court-site filenames, no
text layer) into `~/Downloads/` and asked to run the full RAG-ingest pipeline. All 4 are
**คดีพิพาทสัญญาทางปกครอง** (ค่าปรับ / บอกเลิกสัญญา / ตรวจรับงาน — core procurement domain).

## What We Did (local phase — COMPLETE & verified)
- **OCR** all 4 via `ocr_v4.py` (Gemini 2.5 Pro, 300 DPI), 76 pages → verbatim `_ocr_v4.md`.
- **Verified เลขคดีแดง against high-res headers** — OCR + auto-namer misread 2 files:
  `๒๔๓/๒๕๖๔`→**๗๑๓/๒๕๖๘**, `๑๒๘๒/๒๕๖๗`→**๑๒๕๒/๒๕๖๘** (red-year≠judgment-year tell). Fixed.
- **Structured** to `ref_sac` format via new adapter `pipeline/structure_local_judgments.py`
  (reuses `extract_ac_judgments.EXTRACT_PROMPT` on local verbatim; `extract_ac_judgments.py`
  itself can't run — it pulls from Drive).
- **Uploaded 4 PDFs to Drive folder AC** (`1_NGGLSfMmlaICUNLXZym6MrCfJiWyRfI` — the script's
  `FOLDER_AC_PDF` constant is stale/404), patched real `file_id`/`file_url` into frontmatter.
- **Indexed local Qdrant**: +59 chunks → **34,271**. Normalized `issued_by`→`ศาลปกครอง`
  (matches 147-file convention) and force-reindexed the 3 outliers.
- **Rebuilt BM25 from Qdrant**: 34,271 == 34,271 MATCH. (2,604 dup signatures = pre-existing
  local double-index, NOT from these files.)
- **Verified retrieval**: all 4 rank #1 for targeted queries (hybrid+rerank). Penalty math
  on o_1252 faithful; final page = signature block (not truncation).
- Wrote learning `2026-06-17_court-judgment-case-number-verify-headers.md`.

### The 4 files (all gitignored — live in vault/data, not git-tracked)
| file | เลขคดีแดง | date | parties | file_id |
|------|----------|------|---------|---------|
| ref_sac_o_9_2568    | อ.๙/๒๕๖๘    | 6 ม.ค. 68  | บ.ผลธัญญะ ↔ ทต.ออนใต้      | 1abMqOQwA2ZgZwdQFSD75zKAJIHN9r-z4 |
| ref_sac_o_476_2568  | อ.๔๗๖/๒๕๖๘  | 30 มิ.ย. 68 | หจก.ภักสุธีโกศล ↔ ทต.กะรน  | 1uwk6I7IlqWJCxerGnqjTvMStx70xjAds |
| ref_sac_o_713_2568  | อ.๗๑๓/๒๕๖๘  | 25 ส.ค. 68  | บ.ผลธัญญะ ↔ ทต.ม่วงยาย     | 1biygbA1jD7gSpEtLU6Jjyy8t2m9yeCTV |
| ref_sac_o_1252_2568 | อ.๑๒๕๒/๒๕๖๘ | 3 ธ.ค. 68   | อบต.ละเอาะ ↔ หจก.เค.เอส.บี | 1SRAJhNHSvm9zeq9SttevrRCfVZzy_rO7 |

## Pending
- [ ] **Confirm intent**: Ming asked for "คำพิพากษา 8/2568" before adding these — none is 8/2568
      (closest = อ.๙/๒๕๖๘, header confirmed ๙ not ๘). Confirm these 4 are the intended set,
      or whether a 5th (8/2568) is expected.
- [ ] **Deploy to prod** (mwaprocure.gnim.cloud / 31.97.188.155): SCP 4 MD → `index_md_folder.py`
      → `rebuild_bm25_from_qdrant.py` on prod → verify retrieval. (SSH may need hotspot — ISP block.)
- [ ] **git commit** adapter + learning (the 4 MDs are gitignored, won't commit).
- [ ] Optional: copy 4 MD to Drive `md_backup/` folder (established backup pattern).

## Next Session
- [ ] Get Ming's answer on the 8/2568 intent question.
- [ ] If approved: deploy 4 judgments to prod, replay eval to confirm no regression.
- [ ] Commit `structure_local_judgments.py` + `2026-06-17_court-judgment-case-number-verify-headers.md`.

## Key Files
- `ψ/lab/thai-legal-rag/data/md_backup/ref_sac_o_{9,476,713,1252}_2568.md` (gitignored)
- `ψ/lab/thai-legal-rag/pipeline/structure_local_judgments.py` (new, untracked)
- `ψ/memory/learnings/2026-06-17_court-judgment-case-number-verify-headers.md` (new)
- Verbatim OCR source: `~/Downloads/sac_judgment_o_{9,476,713,1252}_2568_ocr_v4.md` + PDFs
- On branch `fix/stale-cookie-and-rag-improvements` (has uncommitted reranker.py bm25 work — pre-existing)

## State
- Local Qdrant `thai_legal_rag`: 34,271 points. Docker + qdrant container left RUNNING.
- BM25: 34,271, MATCH (local double-index dups pre-existing — replay eval on prod only).
