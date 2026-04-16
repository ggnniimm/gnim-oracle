---
title: # Verify Schema and Results Before Reporting Done (Spreadsheet / Data Updates)
tags: [data-integrity, derived-fields, verify-before-report, spreadsheet, qdrant]
created: 2026-04-14
source: Oracle Learn
---

# # Verify Schema and Results Before Reporting Done (Spreadsheet / Data Updates)

# Verify Schema and Results Before Reporting Done (Spreadsheet / Data Updates)

## Rule
Before saying "done" or "updated" after any data update, query the actual result first.

For spreadsheets:
```python
# ✅ Always print headers first to see full schema
headers = [c.value for c in ws[1]]
print("Columns:", headers)
# Then update ALL relevant columns, not just the one you think matters
```

For databases / Qdrant:
```python
# ✅ Count rows still wrong after patch
remaining = [r for r in rows if r["url"] != expected]
print(f"Still wrong: {len(remaining)}")
```

## Derived Fields Must Be Updated Together
When a source field changes, update ALL fields derived from it in the same script:
- Drive file_id changed → URL column must change too (URL = `https://drive.google.com/file/d/{file_id}/view`)
- Don't update ID column and leave URL stale

## Pattern That Caused the Mistake (2026-04-14, twice)
1. Patched xlsx Drive IDs → did NOT check URL column → reported "done" → Ming asked why URL was wrong
2. Patched Qdrant → did NOT check session files → reported "done" → Ming showed broken links still there

## Root Cause
Ran scripts that targeted only one column/field without reading the schema first.

From: `ψ/memory/retrospectives/2026-04/14/20.08_xlsx-cleanup.md`

---
*Added via Oracle Learn*
