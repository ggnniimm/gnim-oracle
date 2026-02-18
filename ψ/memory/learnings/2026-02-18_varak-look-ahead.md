# Look-ahead beats greedy context in Thai legal วรรค splitting

**Date**: 2026-02-18
**Source**: rrr: gnim-oracle
**Tags**: thai-law, parsing, heuristics, testing

## Pattern

When splitting Thai legal text into วรรค (paragraphs), list-item blocks ((๑)(๒)(๓)) contain continuation text that must merge — but a closing วรรค after the list must NOT merge.

**Greedy approach fails**: enter list context on first marker, merge everything → over-merges closing วรรค (ข้อ 215: "การดําเนินการตามวรรคหนึ่ง..." wrongly merged).

**Look-ahead approach works**: before merging a non-marker paragraph in list context, check if subsequent paragraphs still contain list markers. If yes → between items → merge. If no → list is done → check continuation pattern or exit.

## Algorithm (5-level priority)

1. `_DEFINITE_SUBJECT_RE` (รัฐมนตรี, คณะกรรมการ, etc.) → always exit
2. Current paragraph has embedded list markers → merge (still in block)
3. Subsequent paragraphs have markers → merge (between items)
4. `_LIST_CONTEXT_CONTINUATION_RE` (ทั้งนี้, ในกรณี, etc.) → merge (qualifier)
5. Otherwise → exit list context (new วรรค)

## Key Insight

Synthetic unit tests are necessary but not sufficient for domain-specific parsing. Real data reveals patterns (Gemini's partial merging, multi-level nesting) that synthetic tests miss. Always verify with actual cached/production data.
