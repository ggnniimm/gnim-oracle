---
title: ## Audit Heuristics Need Ground-Truth Validation Before Scale
tags: [audit, heuristics, ground-truth, thai-legal, ocr, oauth]
created: 2026-04-14
source: Thai Legal RAG OCR truncation audit 2026-02-22
---

# ## Audit Heuristics Need Ground-Truth Validation Before Scale

## Audit Heuristics Need Ground-Truth Validation Before Scale

Heuristic-based audits need spot-check validation BEFORE automated fixes run at scale.

**What happened**: Built audit script using proxy metric (ประเด็น vs วินิจฉัย count mismatch) → flagged 27 files → ran automated re-OCR on all → 26 were false positives (had complete สรุปข้อวินิจฉัย).

**Correct truncation signal for Thai กวจ documents**:
- สรุปข้อวินิจฉัย present with bullet content → complete ✓
- Missing สรุปข้อวินิจฉัย → likely truncated ✗
- ประเด็น/วินิจฉัย count mismatch → unreliable (documents genuinely have many sub-answers under one ประเด็น)

**Rule**: Spot-check 3-5 flagged items manually before running automated fix at scale.

**Google OAuth note**: `urn:ietf:wg:oauth:2.0:oob` is deprecated since 2022. Use `flow.run_local_server(port=0, prompt="consent")` — opens browser, starts ephemeral local server, catches redirect automatically.

---
*Added via Oracle Learn*
