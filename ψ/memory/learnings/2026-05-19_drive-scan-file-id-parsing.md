---
name: drive-scan-file-id-parsing
description: Drive scan must parse file_id with regex in frontmatter boundary, not line limit — long frontmatters push file_id past line 20
metadata:
  type: feedback
---

Use regex search within frontmatter (between `---` markers) to find `file_id:`, not `[:20]` line slicing.

Files with many `laws_referenced` entries have frontmatters 25+ lines long — `file_id` gets pushed past line 20 and is missed, falsely reporting the file as "new".

**Fix:**
```python
FILE_ID_RE = re.compile(r'^file_id:\s*["\']?([^"\'\s]+)["\']?', re.MULTILINE)
fm_end = text.find('\n---', 3)  # MUST use \n--- not --- (see second bug below)
fm = text[:fm_end] if fm_end > 0 else text[:2000]
m = FILE_ID_RE.search(fm)
```

**Why:** Discovered when ว242 (with 7 laws_referenced) showed up as "new" in Drive scan despite having an MD. The [:20] line limit was insufficient.

**Second bug (2026-05-19):** `text.find('---', 3)` also matches `---` embedded *inside* file_id values. Example: `ref_sac_o_145_2551.md` has `file_id: "1xo---yIRwuuDpCQeeabeVZ5ByIb78jhH"` — the `---` in the value was found first, cutting the frontmatter before the `file_id:` line completed. Regex then captured only `1xo` instead of the full ID, falsely reporting it as "new". Fix: use `text.find('\n---', 3)` so only `---` at the start of a line matches.

**How to apply:** Any script scanning md_backup for file_ids must use `'\n---'` (not bare `'---'`) as the frontmatter end marker, AND use regex instead of line-limited iteration.
