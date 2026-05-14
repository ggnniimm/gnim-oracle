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

**The damage is worse than missing content — Pro hallucinates.** Audited all 75 raw caches the same day and found ว1489 (`cc210728719b5967_raw.json`) had a page-1 placeholder. The previous structuring run on 05-14 10:49 produced a `quality: good` MD anyway, with content that *looked* fine. After re-OCR with cache cleared, diffing old vs new revealed Pro had **fabricated specific document references** when page 1 was missing:

| Old MD (poisoned) | New MD (correct) |
|---|---|
| อ้างถึง "ว ๘๙๕ ลงวันที่ ๑๐ พ.ย. ๒๕๖๓" | อ้างถึง "คำวินิจฉัยกฤษฎีกา เรื่องเสร็จที่ ๑๓๙๗/๒๕๖๓" |
| หนังสือ "ด่วนที่สุด ที่ นร ๐๙๐๑/๑๕๗๗ ลว. ๑๔ พ.ย. ๒๕๖๕" | (no such reference exists in the doc) |
| พ.ร.บ.วิธีการงบประมาณ **พ.ศ. ๒๕๐๒** | พ.ร.บ.วิธีการงบประมาณ **พ.ศ. ๒๕๖๑** |
| 5 entries in `laws_referenced` | 10 entries (incl. มาตรา ๒๙ วรรคหนึ่ง (๓) และ (๔)) |

Pro invented plausible-looking citation numbers, dates, and the wrong law version. Because they look real, downstream LLM and human reviewers can't catch them. `quality: good` was assigned because the structuring pass succeeded — not because the content was accurate. **This is silent corpus poisoning.**

**How to apply:**
- When OCR retry produces `quality:review-needed` with a missing-page note, inspect the raw cache before blaming the model or network.
- After every long-doc OCR session, audit `data/ocr_cache/*_raw.json` for `"extraction failed"` or `"timed out"` strings before trusting the MDs they produced.
- Treat `quality: good` from per-page Pro pipelines as a process flag, not a content guarantee — if the underlying raw cache had a placeholder, the MD's specific citations/dates/law-versions are suspect.
