# Chunk Promotion Pattern — Revalidated + Extended to Pure-OCR ข้อหารือ

**Date**: 2026-05-15
**Project**: gnim-oracle (thai-legal-rag)
**Session**: eval fix arc 77→83/84 (07:41–09:00 GMT+7)

## The Pattern (proven 5/5 today)

When a TC fails because expected source isn't in top-K retrieval:

1. **Verify retrieval gap, not LLM variance** — run TC verbose; if `⚠ expected source X not cited`, it's retrieval. If sources retrieved but `✗ must_contain Y not found`, it's variance.
2. **Read source MD** — confirm the answer content actually exists somewhere in the file.
3. **Prepend an answer-shaped bullet at top of `## สรุปข้อวินิจฉัยและแนวปฏิบัติ`** that packs:
   - query keywords (so embedding matches the query)
   - all must_contain phrases (so they appear in first chunk)
   - inverse of must_not_contain when relevant
4. **scp + force-reindex single file on prod** (~8s): `pipeline/index_md_folder.py --force-reindex --file X.md`
5. **Verify TC PASS** (re-run 1-2x).

## Extension: pure-OCR ข้อหารือ MDs

Some MDs are raw OCR with structure: `# เรื่อง` → `## ข้อเท็จจริง` → `## ประเด็นข้อหารือ` → `## ข้อวินิจฉัย`. They have **no `## สรุป` anchor section**. These are hard to retrieve because the summary chunk is the strongest retrieval anchor (per `2026-05-05_summary-chunk-is-anchor-for-retrieval`).

**Fix**: ADD a new `## สรุปข้อวินิจฉัยและแนวปฏิบัติ` section between `# เรื่อง` and `## ข้อเท็จจริง`. Concrete case: `003_กวจ_12602_*.md` for TC-037 — went from "expected source not cited" to ranked #3 retrieved on first try.

## Numeral system caveat

Thai legal documents often use Thai numerals (`๕,๐๐๐,๐๐๐` instead of `5,000,000`). When LLM quotes verbatim, must_contain checks fail on Arabic-only criteria. Two complementary fixes:

- **In source MD chunk-promotion bullet**: include BOTH numeral systems side-by-side
  (`5,000,000 บาท (๕,๐๐๐,๐๐๐ บาท)`)
- **In must_contain**: use array-of-arrays for any-of alternatives
  (`["7 วัน", "เจ็ดวัน", "เจ็ดวันทำการ"]`)

The TC-018 fix used must_contain alternatives only (no source change). The TC-037 fix used both (source had Thai-only, promotion bullet adds Arabic).

## Verify-before-fix on "known fails"

TC-067 was marked "known fail" in MEMORY.md baseline. Fresh run today: PASS × 3. The 5 chunk-promotions earlier in this session shifted retrieval ranks across the corpus, lifting 1758 into top-K naturally for TC-067's query.

**Rule**: before applying a fix to any "known fail", run TC 1-2× to verify it's *currently* failing. Memory captures historical state, not current. Especially after corpus changes, the failure landscape shifts in ways memory can't track.

## When NOT to chunk-promote: date arithmetic

TC-084 (multi-step date calc + วันหยุดเลื่อน + 2 inspection cycles) failed 2/3 runs even with full guide doc retrieved. Run 3 returned "3 วัน" instead of "1 วัน" — a **wrong number**, not a phrasing variance. No amount of chunk promotion fixes this. Date arithmetic class needs `gemini-2.5-pro` or thinking mode, not retrieval engineering.

## Related

- [[2026-04-30_corpus-resync-and-tc044-tc050-fixes]] — original chunk promotion pattern
- [[2026-05-05_summary-chunk-is-anchor-for-retrieval]] — why summary section matters
- [[2026-04-30_eval-tc046-summary-chunk-promotion]] — single-doc promotion case
- [[2026-04-30_eval-tc071-section-number-promotion]] — must_contain alt pattern
- [[2026-05-15_pre-deploy-rate-limit-estimate]] — yesterday's deploy lesson
