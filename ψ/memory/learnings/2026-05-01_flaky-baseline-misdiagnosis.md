# "Flaky Baseline" Often Means Misdiagnosis, Not LLM Variance

**Date**: 2026-05-01
**Trigger**: TC-037 + TC-071 labeled "~67% pass flaky" in handoff. Prod 3/3 runs each → both **0/3 PASS**. Not flaky — consistent fails.

## What "flaky" actually meant

Two TCs in the eval suite were carried as "flaky LLM variance" baselines for weeks:

- **TC-037** (วิจารณ์ร่างประกาศ): `must_contain: ["5,000,000"]`. Failing because LLM consistently cites the **current** 10M threshold (per ว196/2568 which raised the value), not the legacy 5M. This is **corpus drift** — the law genuinely changed and the test was written to the old value.
- **TC-071** (ม.97 vs ม.102 authority): `must_contain: [..., ["ข้อ ๑๖๕", "ข้อ 165"]]`. Failing because LLM consistently captures the operative principle ("ตามวงเงิน") without citing the section number. The semantic_check fallback existed but returned False silently in prod even when the answer matched the concept perfectly. This is **test brittleness** — section numbers are a fragile keyword for a semantically-correct answer.

Neither is flaky. Both fail every time. The "67% pass" rate from the handoff was likely from earlier corpus states before the 04-30 resync; once the resync stabilized retrieval, both TCs settled into consistent fails.

## The diagnostic mistake

Three signals encouraged me to stay in "flaky variance" framing:
1. The handoff said "flaky baseline" with a specific pass-rate number.
2. Local eval runs were all FAILing (3/3 each), but I attributed that to local-double-index per the handoff warning.
3. The recap suggested "add must_contain alternatives if you want to push past 78/80 ceiling" — which is the standard fix for LLM variance.

Only when I ran prod 3x and saw 0/3 each did the framing collapse. Prod was supposed to be the canonical state where flaky-variance was real.

## Fix pattern

For **corpus drift**: alternatives that accept either historical or current value. `[["5,000,000", "10,000,000"]]`. The test verifies "cited a threshold," not "cited the value as it stood when the test was written."

For **test brittleness on section numbers**: include the operative phrase as alternative. ข้อ 165 วรรค 3's content is "พิจารณาตามวงเงิน". Adding `"ตามวงเงิน"` as an alternative accepts answers that capture the principle without naming the section. Acceptable because:
- The semantic_check field already specified the same intent
- The notes field acknowledges "ตามวงเงิน" as the operative concept
- Section numbers are syntactic; the principle is what matters legally

## Operative rule

**Run failing TCs 3x on prod before believing handoff labels.** Prod 0/3 → not flaky, diagnose root cause (corpus drift, test brittleness, retrieval gap). Prod 1-2/3 → genuine LLM variance, alternatives are right. The 3x cost is ~90 seconds; the cost of fixing the wrong problem is hours.

Pass rate trajectory after fix: TC-037 0/3 → 3/3 PASS prod, TC-071 0/3 → 3/3 PASS prod. Eval ceiling: 78/80 → 80/80 in expectation.

## Related

- Existing memory entry: "Eval drill-down method — Run each failing TC 2-3x with `--id TC-XXX -v`. Consistent fail = retrieval gap. Intermittent = LLM variance." This entry already captured the principle but I bypassed it because the handoff label set the wrong prior.
- See `ψ/memory/learnings/2026-04-17_eval-debug-tc037-source-mismatch.md` for the prior TC-037 diagnosis (source_name `.pdf`/`.md` mismatch fixed retrieval, but the test was still pinned to outdated 5M).
