---
date: 2026-04-02
type: pattern
tags: [naming, architecture, data-pipeline]
---

# Field names should match the source of truth end-to-end

## Context

`md_loader.py` renamed frontmatter fields when loading:
- `file_id` → `source_drive_id`
- `file_url` → `source_url`

This created confusion: frontmatter said one thing, Qdrant payload said another, Streamlit app reconstructed URLs from IDs instead of using the URL directly. Three layers of unnecessary indirection.

## Lesson

When data flows through a pipeline (frontmatter → loader → index → app), keep field names identical at every stage. "Normalization" that only renames without transforming adds a translation layer that confuses every future reader.

If the source document says `file_id`, the index should say `file_id`, and the app should read `file_id`.

## Applied

Renamed `source_drive_id` → `file_id` and `source_url` → `file_url` across 12 Python files. Streamlit app now uses `file_url` directly instead of constructing URL from `drive_id`.
