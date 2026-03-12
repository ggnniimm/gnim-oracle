# Excel Is Not Ground Truth for Legal Documents

**Date**: 2026-03-06
**Context**: Reconciling OAG rulings (md_backup vs Excel spreadsheet)

## Pattern

When using a spreadsheet as the "master list" for legal document reconciliation, **always cross-check with the domain expert before bulk deletions**. Spreadsheets contain human data entry errors that compound when used programmatically.

## Evidence

Excel had 280 entries for OAG rulings. Automated comparison found 48 "extra" files to remove. After removal, Ming corrected 5 entries:

| Excel Said | Reality | Error Type |
|---|---|---|
| 3/2563 | 7/2563 | Wrong number |
| 19/2562 | 19/2552 | Wrong year (decade off) |
| 49/2562 | 49/62 | Short year format |
| 119/2562 | 119/2566 duplicate | Wrong year column |
| 132/2564 | 132/2566 duplicate | Wrong year column |

2 of these corrections meant we'd deleted valid files. Recovered from OCR cache.

## Lesson

1. **Show the "extra" list to human before deleting** — especially outliers (e.g., 2552 among 2561-2567 files should have raised a flag)
2. **Multiple data layers save you** — OCR cache preserved content even after md files were deleted
3. **Stage deletions** — move to temp dir first, delete after confirmation. `os.remove()` on untracked files is irreversible without cache backup.

## Tags

data-pipeline, reconciliation, safety, domain-knowledge, legal-documents
