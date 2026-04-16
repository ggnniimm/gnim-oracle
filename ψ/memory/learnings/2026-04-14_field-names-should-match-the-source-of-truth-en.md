---
title: ## Field Names Should Match the Source of Truth End-to-End
tags: [naming, architecture, data-pipeline, field-names, source-of-truth]
created: 2026-04-14
source: 2026-04-02 learning
---

# ## Field Names Should Match the Source of Truth End-to-End

## Field Names Should Match the Source of Truth End-to-End

When data flows through a pipeline (frontmatter → loader → index → app), keep field names identical at every stage. "Normalization" that only renames without transforming adds a translation layer that confuses every future reader.

**Anti-pattern**: `md_loader.py` renamed `file_id` → `source_drive_id` and `file_url` → `source_url`. This created three layers of indirection: frontmatter said one thing, Qdrant payload said another, app reconstructed URLs from IDs instead of using the URL directly.

**Rule**: If the source document says `file_id`, the index should say `file_id`, and the app should read `file_id`.

**Applied**: Renamed `source_drive_id` → `file_id` and `source_url` → `file_url` across 12 Python files. Streamlit app now uses `file_url` directly instead of constructing URL from `drive_id`.

---
*Added via Oracle Learn*
