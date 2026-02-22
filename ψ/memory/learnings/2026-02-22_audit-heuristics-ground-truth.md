# Lesson: Audit Heuristics Need Ground-Truth Validation

**Date**: 2026-02-22
**Source**: thai-legal-rag OCR truncation audit
**Context**: Fix pipeline for 27 flagged OCR-truncated MD files — 26 turned out to be fine

## The Pattern

Heuristic-based audits need spot-check validation *before* automated fixes run at scale.

## What Happened

Built an audit script using a proxy metric: count of ประเด็นข้อหารือ references vs count of numbered ข้อวินิจฉัย items. Discrepancy → flagged as possibly truncated. Ran automated re-OCR on 27 files. Result: 1 was genuinely truncated (confirmed earlier), 26 were false positives — all had complete `## สรุปข้อวินิจฉัย` sections.

## The Correct Signal

For Thai กวจ legal documents:
- **สรุปข้อวินิจฉัย present with bullet content** → document is complete ✓
- **Missing สรุปข้อวินิจฉัย** → likely truncated ✗
- ประเด็น/วินิจฉัย count mismatch → unreliable (documents genuinely have many sub-answers under one ประเด็น)

## Rules Going Forward

1. **Spot-check 3-5 flagged items manually before running automated fix at scale**
2. Use `## สรุปข้อวินิจฉัย` presence as primary truncation signal, not count heuristics
3. If fixing requires external resources (Drive API), validate access on 1 file first, then queue the rest

## Google OAuth Note

`urn:ietf:wg:oauth:2.0:oob` is deprecated since 2022. Use:
```python
creds = flow.run_local_server(port=0, prompt="consent")
```
This opens browser, starts ephemeral local server, catches redirect automatically. No manual code entry needed.
