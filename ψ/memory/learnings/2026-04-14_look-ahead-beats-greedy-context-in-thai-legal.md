---
title: ## Look-Ahead Beats Greedy Context in Thai Legal วรรค Splitting
tags: [thai-law, parsing, look-ahead, list-items, วรรค]
created: 2026-04-14
source: rrr: gnim-oracle 2026-02-18
---

# ## Look-Ahead Beats Greedy Context in Thai Legal วรรค Splitting

## Look-Ahead Beats Greedy Context in Thai Legal วรรค Splitting

When splitting Thai legal text into วรรค, list-item blocks ((๑)(๒)(๓)) contain continuation text that must merge — but a closing วรรค after the list must NOT merge.

**Greedy approach fails**: enter list context on first marker, merge everything → over-merges closing วรรค.

**Look-ahead approach works**: before merging a non-marker paragraph in list context, check if subsequent paragraphs still contain list markers. If yes → between items → merge. If no → list is done → check continuation pattern or exit.

**5-level priority algorithm**:
1. `_DEFINITE_SUBJECT_RE` (รัฐมนตรี, คณะกรรมการ, etc.) → always exit
2. Current paragraph has embedded list markers → merge (still in block)
3. Subsequent paragraphs have markers → merge (between items)
4. `_LIST_CONTEXT_CONTINUATION_RE` (ทั้งนี้, ในกรณี, etc.) → merge (qualifier)
5. Otherwise → exit list context (new วรรค)

**Key insight**: Synthetic unit tests are necessary but not sufficient for domain-specific parsing. Real data reveals patterns that synthetic tests miss. Always verify with actual production data.

---
*Added via Oracle Learn*
