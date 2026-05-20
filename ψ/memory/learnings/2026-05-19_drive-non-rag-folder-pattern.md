---
name: drive-non-rag-folder-pattern
description: Non-RAG Drive files (contractor lists, registries) should be moved to a skip folder rather than Trashed, so they don't reappear in future scans
metadata:
  type: feedback
---

When a Drive PDF has no RAG value (contractor lists, registries, non-legal content), move it to a designated skip folder rather than Trash.

**Pattern used:**
- `non-RAG` folder — for CGD3 misc files (contractor lists, 63MB unknowns)
- `non-procurement-OAG` folder — for OAG files outside procurement scope (299 files)

These folders are NOT in `folder_ids` dict in scan scripts → never appear as "new" in future scans.

**Why:** Trash is reversible within 30 days, but move-to-folder is permanent-ish and more intentional. Files stay accessible for reference without polluting the scan pipeline. Also avoids re-deciding the same files if they somehow get re-added.

**How to apply:** When bulk Drive cleanup finds a category of non-RAG files, create one dedicated folder per category and move there. Don't Trash unless truly unwanted. Update scan script's `folder_ids` dict to exclude these folders.

See also [[drive-scan-file-id-parsing]] for the scan correctness fix from same session.
