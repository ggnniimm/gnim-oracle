# Hybrid Model Routing — Per-Query Domain Detection

**Date**: 2026-05-15
**Project**: gnim-oracle (thai-legal-rag)
**Session**: 13.37_hybrid-pro-routing-and-84-84

## The Pattern

When a small subset of query types fail consistently on a cheap/fast model but pass on a more capable/expensive one, **route per-query** instead of upgrading universally. Preserves UX + cost for the 95% case; surgical fix for the failing class.

```python
# generator.py
_FORCED_MODEL = os.getenv("GENERATOR_MODEL") or None
_THAI_MONTH_RE = re.compile(r"(?:มกราคม|กุมภาพันธ์|...)")

def _is_date_calc_query(q: str) -> bool:
    return "ค่าปรับ" in q and bool(_THAI_MONTH_RE.search(q))

def _pick_model(q: str) -> str:
    if _FORCED_MODEL:
        return _FORCED_MODEL
    return GEMINI_PRO_MODEL if _is_date_calc_query(q) else GEMINI_FLASH_MODEL
```

Plus a `GENERATOR_MODEL` env-var override that **bypasses routing** for experiments and emergency rollback.

## Why It Beat Alternatives

| Approach | Cost | UX | Correctness | Verdict |
|---|---|---|---|---|
| Full swap Flash→Pro | 5-10× per call | All queries slow (60-90s) | Best | Rejected — UX regression for non-date-calc |
| Env-toggle (eval-only Pro) | Cheap | UX preserved | Tests pass, prod doesn't fix users | Rejected — doesn't help real users |
| **Hybrid routing** | 5-10× per call only on 4/84 = ~5% of queries | UX preserved for 95% | Date-calc class fixed | **Shipped** |

## Detection Heuristic — Keep It Trivial

Advisor's call: "Don't over-engineer the classifier. A 2-line check is enough; resist count-based or score-based heuristics until you have a documented false-positive that hurts."

Scan against eval corpus before shipping. The 84-TC scan showed:
- 4 routed (TC-081/082/083/084) — exactly the intended set
- 1 false-positive (TC-081) — but it PASSes on Flash already, so cost-only no correctness harm
- Other 80 untouched

**False-positives that are correctness-safe are cheap; false-negatives that miss the problem are expensive.** Tune toward over-routing if you must err.

## Sample-Size Discipline for Variance

Before declaring "fixed", run ~10 samples not 3. Pro on TC-082:
- Yesterday smoke test: 9/9 PASS → felt like 100%
- Today full eval: 0/1 FAIL → revised
- Variance check: 3/3 PASS → 12/13 = ~92%

3 samples can't distinguish 100% from 90%. The variance check matters.

Rule of thumb:
- 3/3 = "looks good, retest"
- 9/10 = "probably ~90%"
- 19/20 = "probably ~95%"

For RAG eval where each call is expensive/slow, 10 runs is the practical floor for variance estimation.

## When To Reach For This Pattern

1. Eval reveals a **problem class** (not just one TC) failing on Flash — e.g. date-calc, multi-step math, ambiguous-citation parsing
2. The class is **detectable from query** (regex/keyword feasibility)
3. Upgrade fixes it (verified before designing routing, per [[2026-05-15_verify-premise-first]])
4. The class is **small enough** that 5-10× cost on it is acceptable
5. Latency on the routed class is **tolerable** (60-90s for date-calc is fine because users expect math to think; would not be fine for "what's a procurement method")

## Counter-Patterns to Avoid

- **Universal upgrade** "just to be safe" → UX regression for 95% of queries
- **Multi-tier scoring** of query "complexity" → premature abstraction, harder to debug
- **Routing based on retrieval features** → couples generator decision to retrieval state, hard to reason about
- **Hard-coded TC-specific patches** in generator → not a pattern, just brittleness

## Pair With

- `[[2026-05-08_gemini-embedding-2-ga-alias-zero-cost-migration]]` — similar "minimal-touch deploy when prod has uncommitted drift" pattern
- `[[2026-05-01_flaky-baseline-misdiagnosis]]` — sample-size lessons (3/3 ≠ proven)
- TC-071 / TC-015 test-brittleness pattern: LLM uses parent term; add to must_contain alternatives

## Verified

- 9/9 PASS in step-3 smoke test (TC-082/083/084 × 3, default thinking-on)
- 12/13 PASS combined across 13 runs of TC-082 (single full-eval miss)
- 3/3 PASS for TC-015 after must_contain expansion
- 80/80 PASS for the non-routed (Flash) TCs in full eval
- Mwaprocure UX unchanged (no `.env` mutation, default routing only fires for date-calc)
- Backups left on prod: `.bak.pre-pro-experiment`, `.bak.pre-pro-routing`

## Commits

- `bfd2f2d` — feat(gen): route date-calc queries to gemini-2.5-pro
- `7a95162` — fix(eval): TC-015 must_contain accept parent term

## Caveats

- Pro on Vertex `location=global`, default thinking-on (max 8K thinking tokens auto-budgeted). Cannot disable for 2.5-pro. If thinking ever becomes too aggressive, can cap with `thinking_config=ThinkingConfig(thinking_budget=N)` (range 128-32768).
- Detection regex is Thai-month names + ค่าปรับ. If new date-calc TCs use other formulations (e.g. Buddhist year format, day-of-week computation), regex needs extension.
- If Flash infra has a bad day (503 retry storms — seen today with full eval 3× over ETA), Pro queries may also slow. Fallback chain on Pro now steps down to Flash explicitly, then flash-lite, then flash-latest.
