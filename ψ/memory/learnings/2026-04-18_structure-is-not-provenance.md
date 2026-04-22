---
name: Document structure does not prove content provenance
description: Being in section X doesn't mean the text is original — OCR files get edited; always verify against PDF source
type: feedback
date: 2026-04-18
---

When verifying whether text in an MD file is original OCR content or an injected cross-ref, document structure alone is insufficient evidence.

**Why:** OCR files in this project get edited to add cross-refs regardless of which section the text appears in. A citation in `## ข้อวินิจฉัย` COULD be original, but it could also have been injected there. The only proof is the source PDF.

**How to apply:** When user asks "is this original or injected?" — do not answer from section name. Go straight to: (1) git history if tracked, (2) PDF source (Google Drive). If Drive MCP is unavailable, suggest `! open "https://drive.google.com/file/d/<id>/view"` so Ming can verify directly.
