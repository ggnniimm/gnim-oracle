---
title: ## Thai Legal Parsing Debug Workflow: Systematic Diff Reduction (2026-02-18 to 2
tags: [thai-legal, parsing, debug, varak, unicode, ocr, comparison-tool, gemini, codespace]
created: 2026-04-14
source: retro: 2026-02-18 to 2026-02-21 debug sessions
---

# ## Thai Legal Parsing Debug Workflow: Systematic Diff Reduction (2026-02-18 to 2

## Thai Legal Parsing Debug Workflow: Systematic Diff Reduction (2026-02-18 to 2026-02-21)

**Test with real data, not just synthetic fixtures**: Unit tests pass ≠ works on real Thai legal text. Real documents have patterns (embedded markers from Gemini, curly quotes, multi-level list nesting) that synthetic tests miss. Always verify against actual cache data after each fix.

**Unicode curly quotes in Thai legal PDFs**: Thai legal PDFs use `\u201c` / `\u201d` (curly quotes), not ASCII `"`. When regex doesn't match visually identical text, print `hex(ord(c))` to detect invisible character differences.

**Look-ahead beats greedy context for list merging**: A greedy "enter context, merge everything" approach always over-merges. Check if there are more structural markers ahead before deciding to merge. No markers ahead + no continuation pattern = list is done.

**Under-splits need JSON cache patches, not rule tweaks**: When Gemini merges what should be separate วรรค, fix the JSON cache directly with exact string matching. Rules can't help because the text structure looks correct — the problem is semantic.

**`has_blank_sep` is a strong structural signal**: Blank lines between a short non-legal line and previous content are nearly always OCR artifacts from section headings.

**OCR truncation is a hard ceiling**: When expected > got and section text simply doesn't have the content, document it and move on. Don't treat parser failures and OCR gaps the same way.

**--cleanup danger**: `--resplit`/`--cleanup` flags run Gemini on ALL sections. If Gemini API key is wrong → diffs explode. Always verify key before running. Consider `--lock` annotation for manually-patched sections.

**Codespace data availability**: Check data availability first before planning data-dependent work. If configuration points to a data directory and it's empty, ask immediately — don't spend 10 minutes searching.

**Build comparison tools early**: A `compare_sections.py` that maps Excel reference to JSON cache is essential for measuring progress. Data-independent work (writing the comparison script, writing tests) can proceed even without OCR cache.

---
*Added via Oracle Learn*
