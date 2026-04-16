---
title: ## Google Drive API Is Available in Codebase
tags: [google-drive, api, integration, thai-legal]
created: 2026-04-14
source: Thai Legal RAG 2026-03-22
---

# ## Google Drive API Is Available in Codebase

## Google Drive API Is Available in Codebase

`src/ingestion/drive.py` provides OAuth2 access to Google Drive:
- `list_files(folder_id)` — list files in a folder
- `list_pdfs(folder_id, recursive)` — list PDFs
- `stream_pdf(file_id)` — download PDF bytes directly

Folder IDs in `.env`: `DRIVE_FOLDER_ETC`, `DRIVE_FOLDER_AC` (admin court judgments), `DRIVE_FOLDER_CGD` (กรมบัญชีกลาง), and more (LAW, OAG, AC_MD, etc.)

**Key lesson**: Don't say "I can't access Google Drive" — check the codebase first. The integration already exists.

---
*Added via Oracle Learn*
