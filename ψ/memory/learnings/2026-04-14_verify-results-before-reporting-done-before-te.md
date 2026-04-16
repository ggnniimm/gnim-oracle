---
title: ## Verify Results Before Reporting Done
tags: [verify, workflow, data-integrity, spreadsheet, database, reporting]
created: 2026-04-14
source: 2026-04-14 learning
---

# ## Verify Results Before Reporting Done

## Verify Results Before Reporting Done

Before telling Ming "done" or "updated", always query the actual result first.

- Spreadsheet: print headers first, then SELECT sample rows after update
- Database: count rows still wrong after patch
- File: read file back to verify — don't assume from exit code

**Anti-pattern**:
```python
# ❌ Update then immediately report done
ws[row][7].value = new_id
wb.save(path)
print("Updated!")  # ← Didn't know there was a URL column too
```

**Correct pattern**:
```python
# ✅ See schema first, then update all derived fields together
headers = [c.value for c in ws[1]]
print("Columns:", headers)  # ← Know all columns before updating
```

**Pattern occurred twice in one day (2026-04-14)**:
1. Patched Qdrant with xlsx data (didn't verify xlsx was correct first)
2. Updated xlsx Drive ID but not URL column (didn't check schema first)

**Rule**: Before reporting completion, query the real result. Don't assume from exit code.

---
*Added via Oracle Learn*
