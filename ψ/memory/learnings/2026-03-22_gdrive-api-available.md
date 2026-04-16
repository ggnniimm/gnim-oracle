---
name: gdrive-api-available
description: Google Drive API integration exists in src/ingestion/drive.py — always check before saying can't access
type: learning
date: 2026-03-22
---

# Google Drive API is Available in Codebase

`src/ingestion/drive.py` provides OAuth2 access to Google Drive with:
- `list_files(folder_id)` — list files in a folder
- `list_pdfs(folder_id, recursive)` — list PDFs
- `stream_pdf(file_id)` — download PDF bytes directly

Folder IDs in `.env`:
- `DRIVE_FOLDER_ETC` = `1HO_XcrMKaEWIcPa-es6eHuF3pjAAJalf`
- `DRIVE_FOLDER_AC` = admin court judgments
- `DRIVE_FOLDER_CGD` = กรมบัญชีกลาง
- And more (LAW, OAG, AC_MD, etc.)

**Key lesson**: Don't say "I can't access Google Drive" — check the codebase first. Ming will correct you.
