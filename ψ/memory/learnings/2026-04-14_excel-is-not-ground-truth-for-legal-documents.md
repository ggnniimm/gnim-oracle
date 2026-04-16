---
title: ## Excel Is Not Ground Truth for Legal Documents
tags: [data-pipeline, reconciliation, safety, legal-documents, excel]
created: 2026-04-14
source: OAG rulings reconciliation 2026-03-06
---

# ## Excel Is Not Ground Truth for Legal Documents

## Excel Is Not Ground Truth for Legal Documents

When using a spreadsheet as "master list" for legal document reconciliation, always cross-check with domain expert before bulk deletions. Spreadsheets contain human data entry errors that compound when used programmatically.

**Evidence**: Excel had 280 OAG ruling entries. Automated comparison found 48 "extra" files to delete. After removal, 5 corrections needed: wrong numbers (3/2563 → 7/2563), wrong year decade (2562 → 2552), short year format (49/62 ≠ 49/2562).

2 corrections meant valid files were deleted. Recovered from OCR cache.

**Rules**:
1. Show "extra" list to human before deleting — flag outliers (e.g., year 2552 among 2561-2567 files)
2. Multiple data layers save you — OCR cache preserved content after MD deletion
3. Stage deletions — move to temp dir first, delete after confirmation. `os.remove()` on untracked files is irreversible without cache.

---
*Added via Oracle Learn*
