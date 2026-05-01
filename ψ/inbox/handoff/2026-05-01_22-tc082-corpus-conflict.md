# Handoff: TC-082/083/084 attempt — corpus-vs-test conflict found, reverted

**Date**: 2026-05-01 evening
**Status**: tree clean, prod reverted, ready to sleep

## What happened today (after the morning's TC-037/TC-071 fixes)

Tried to fix TC-082/083/084 (date-arithmetic TCs) by adding worked examples to the generator prompt. Mixed results:

| State | TC-082 | TC-083 | TC-084 | Aggregate |
|-------|--------|--------|--------|-----------|
| 0 examples (baseline) | 0/3 | 0/3 | 0/1 | 0/9 |
| 1 example (re-deliv+shift) | 1/2 | 2/2 | 0/5 | 3/9 |
| 2 examples (+ early+shift) | 0/3 | 2/3 | 3/3 | 5/9 |

Each new example pulled the LLM toward case-pattern-matching, fixing one TC and breaking another. Whack-a-mole.

## Key finding: corpus-vs-test conflict on TC-082

Doc `02_กวจ_51349_101164_ข้อหารือวิธีการคำนวณค่าปรับ.md` contains BOTH:
1. **The question** (ประเด็นข้อหารือ): "is it correct to count from day after **original** deadline?"
2. **The ruling** (ข้อวินิจฉัย): the OPPOSITE — "**การคิดค่าปรับตามสัญญา ต้องนับถัดจากวันที่เริ่มทำการใหม่**" (count from new business day)

The LLM consistently cites the question text and ignores the ruling. This is why TC-082 stays at 0% regardless of prompt tweaks. The ruling supports the test's expected value of 18 — the test is right; the LLM is reading the wrong section of the doc.

## What was reverted

- Local `src/generation/generator.py` → reverted via `git checkout`
- Prod container `/app/src/generation/generator.py` → reverted via `docker cp` (verified, no ตัวอย่างที่ 3)
- Prod state: original prompt, no docker image rebuild needed (the change was only docker cp'd, never built into image)

## Decisions for tomorrow

1. **Path A — corpus surgery on doc 51349**: rearrange so the ruling (ข้อวินิจฉัย) is more prominent in chunks than the question. Likely fix for TC-082. Risk: modifying actual legal-doc content.
2. **Path B — accept TC-082/084 as out-of-scope**: mark as known limitations, focus on TC-083 (which the prompt change does fix cleanly).
3. **Path C — semantic_check fallback on TC-082/083/084**: similar to TC-071 fix — if keyword fails, ask Gemini Flash if the answer's calculation is correct semantically. May or may not work for arithmetic.
4. **Path D — drop these TCs**: they're testing arithmetic-with-Thai-holiday-rules, not legal-knowledge retrieval. Different problem class.

## Suite state at end of day

- Legacy 80-TC suite: **79/80** (TC-003 only remaining flaky)
- Full 84-TC suite: **80/84** (TC-003, TC-082, TC-083, TC-084)
- TC-037 + TC-071 fixes from this morning are committed and stable on prod

## Files

- Earlier in day commits: `0515399` (TC-037/TC-071 fix), `9088d8b` (memory)
- This evening: nothing committed (rolled back)

## Sleep well 🌙
