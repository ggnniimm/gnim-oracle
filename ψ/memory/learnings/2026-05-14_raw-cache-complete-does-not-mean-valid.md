---
name: raw-cache-complete-does-not-mean-valid
description: OCR raw cache "complete" only means all page entries exist — not that content is valid. Placeholder entries from old timeouts silently poison subsequent retries.
metadata:
  type: feedback
---

**Raw cache "complete" ≠ content valid — always inspect page entries before trusting the skip.**

When `pdf_to_markdown` sees a raw cache with all page entries present, it reports "Raw cache complete (N pages) — skipping re-extraction" and skips per-page extraction entirely. This is a correctness assumption that can fail silently.

**The failure mode**: A previous extraction attempt timed out on page N, writing a placeholder entry like:
```
<!-- Page 6 -->
[หน้า 6: extraction failed — The read operation timed out]
```
The cache now has N entries (looks "complete"), but page N is junk. A retry that clears no cache will reuse this placeholder, produce a quality:review-needed result, and the root cause stays hidden.

**How to debug**: Read the `_raw.json` cache directly:
```python
import json
data = json.load(open('data/ocr_cache/<hash>_raw.json'))
for i, p in enumerate(data):
    print(f"Page {i+1}: {len(str(p))} chars — {repr(str(p)[:80])}")
```
Placeholder entries are tiny (50–100 chars) and contain "extraction failed".

**Fix**: Delete the `_raw.json` cache file, then re-run with `force=True`. The per-page extraction will redo all pages, and any failures will trigger the 200 DPI fallback (commit `1cdc1dc`).

**Why:** Discovered during ว119 corpus cleanup (2026-05-14). Page 6 timed out in an old run, was cached as placeholder. Two subsequent retries silently reused the placeholder because cache looked "complete". Root cause found only by reading JSON directly.

**How to apply:** When OCR retry produces quality:review-needed with a missing-page note, check the raw cache before assuming it's a model or network problem. The cache itself may be the issue.
