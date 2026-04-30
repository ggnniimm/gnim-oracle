# Corpus gap discovered: 598 files between Drive and md_backup (2026-04-30)

## What

Drive has **1,831 files**. Prod md_backup has **1,233 MDs** (verified parity with local md_backup per yesterday's deploy). **Gap: 598 files (~33% of corpus).**

## Drive inventory by folder

| Folder | Drive count | Notes |
|---|---|---|
| OAG | 556 | สำนักงานอัยการสูงสุด opinions |
| CGD | 540 | กรมบัญชีกลาง — main |
| CGD_OLD | 213 | older กรมบัญชีกลาง docs |
| CGD3 | 182 | newer กรมบัญชีกลาง |
| AC | 159 | **Administrative Court rulings (ref_*)** — all 159 missing from md_backup |
| CGD_W | 148 | กรมบัญชีกลาง — supplementary |
| LAW | 33 | core laws/regulations |

`ref_*` files in Drive: 159, in md_backup: **0**.

## Impact on eval

Audit of failing TCs against md_backup contents:

| TC | Expected sources | Status |
|---|---|---|
| TC-063 | ref_sac_o_483_2551, ref_sac_o_1142_2568 | both missing |
| TC-064 | ref_sac_cmd_262_2566, ref_sac_cmd_289_2564 | both missing |
| TC-065 | ref_sac_o_785_2550, ref_sac_o_83_2555 | both missing |
| TC-066 | ref_sac_o_233_2553, ref_sac_o_72_2564 | both missing |
| TC-067 | 1758, 32616, ref_sac_o_351_2556 | 2/3 present, ref_* missing |
| TC-074 | ref_sac_o_16_2547 | missing |
| TC-075 | ref_sac_o_401_2558 | missing |

**6 of 9 hard fails are corpus-gap, not retrieval/generation.** No prompt or cross-ref work will fix them without first adding the missing court-judgment refs.

TC-071 and TC-076 are NOT corpus-gap — fixable in current corpus (TC-071 fixed today to 2/3 PASS; TC-076 has no expected_sources, pure must_contain).

## Origin

Per yesterday's handoff: 04-29 Drive remap deploy claimed "1,233 MDs (parity with local)". That parity was prod-vs-local, not Drive-vs-local. **Local has always been ~33% behind Drive.** The ref_sac_* files exist in Drive but were never OCR'd to MD form (or were OCR'd then removed pre-2026-04-29).

Side evidence: `bm25.pkl.bak.2026-04-29` (BM25 backup from before the remap) DOES contain `ref_sac_o_16_2547` as a string — meaning at SOME point the ref was indexed. So it may have been OCR'd previously and removed during a prior cleanup, not just never created.

## Three honest paths forward

### A. Accept current corpus, mark 6 TCs as "needs corpus completion"
- 0 work today
- Pass rate ceiling: ~71/80 (in expectation, after today's fixes)
- Document the 6 TCs as deferred / outside-scope

### B. OCR + index just the 16 missing ref_sac_* files referenced in eval
- ~30-60 min: download from Drive, OCR via Gemini, generate MD frontmatter, `index_md_folder.py --force-reindex`
- Pass rate ceiling: ~77/80 (in expectation)
- Targeted, bounded scope

### C. OCR + index all 598 missing files (full Drive sync)
- Hours of OCR + indexing + sanity-checking
- Pass rate ceiling: 80/80 in best case
- Architectural: prod + local fully match Drive going forward
- Scope expansion — would also need to handle the ~440 non-ref files

Recommended: **B** for next session — bounded, high-leverage, matches the current eval's expected_sources without expanding scope to the full Drive.

## Caveats

- The 159 ref_* in Drive are PDFs; OCR via Gemini is needed (per existing pipeline at `pipeline/regenerate_sections.py` or similar)
- Frontmatter for ref_sac_* needs the `ref_*_*_*` naming convention preserved as `original_filename` so eval's substring match works
- Each ref_sac_* PDF is small (court rulings are typically 1-3 pages) — OCR cost is low

## Files

- Drive mapping: `/tmp/drive_mapping.json` on prod (1,831 entries)
- Audit script: `/tmp/audit_expected_sources.py` (local + prod copies, runnable inside docker)
