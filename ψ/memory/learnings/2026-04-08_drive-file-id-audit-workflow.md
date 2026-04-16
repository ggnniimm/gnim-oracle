---
date: 2026-04-08
source: "rrr: gnim-oracle-qdrant"
tags: [google-drive, file-id, audit, oauth, data-integrity]
---

# Drive file_id Audit Workflow

## Pattern
When Google Drive folders are reorganized (files moved between folders), all `file_id` references in MD frontmatter become stale (HTTP 403). This is silent — no error until someone clicks the link.

## Audit Steps
1. Extract unique `file_id` from all MD frontmatter
2. Parallel curl check: `xargs -P 20 curl -s -o /dev/null -w "%{http_code} {}\n"`
3. For 403s: identify which Drive folder the PDF moved to
4. Update `file_id` and `file_url` in frontmatter via regex

## Key Gotchas
- **OAuth token expiry**: Error says "Drive API not enabled" but real issue is expired token. Always `refresh_token` first.
- **`startswith` matching is dangerous for Thai filenames**: `กฎกระทรวง+กำหนดพัสดุ` matches both `กฎกระทรวง+กำหนดพัสดุ.md` and `กฎกระทรวง+กำหนดพัสดุที่รัฐต้องการส่งเสริม...md`. Use exact stem matching.
- **Duplicate file_ids across MDs**: 26 groups of MDs share the same file_id (PDF compilations containing multiple คำวินิจฉัย). This is expected, not a bug.
- **Gemini 503 is per-endpoint**: Classification API may succeed while extraction API fails. No correlation.

## Recovery
OAuth token location: `/Users/mingsaksaengwilaipon/gnim-oracle/ψ/lab/sample-docs/token.json`
Refresh via `client_id`/`client_secret`/`refresh_token` → POST `https://oauth2.googleapis.com/token`
