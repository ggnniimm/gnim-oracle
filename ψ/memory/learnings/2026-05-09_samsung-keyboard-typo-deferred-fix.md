# Samsung Thai keyboard เเ→แ — input normalization deferred

**Date**: 2026-05-09
**Source**: gnim-oracle/thai-legal-rag — investigation of user 00081698's chat session
**Confidence**: High (empirical A/B verified on prod 2026-05-09)

## TL;DR

**Don't deploy query-side `เเ → แ` normalization in isolation** — it makes retrieval *worse* for the query that motivated the fix. Ship it only **together with** changes to query-expansion stability (e.g. raise `ORIGINAL_QUERY_BOOST`, tighten `query_expand` prompt, or add glossary entries that pin specific docs).

## Discovery chain

1. User `00081698` asked: **"ขอแบบฟอร์มใช้แจ้งปลัดกระทรวงการคลังเกี่ยวกับผู้ทิ้งงาน"** (visually correct, with `แ`).
2. UI screenshot confirms user typed `แ` (one character).
3. JSON storage at `/app/data/chat_sessions_00081698.json` shows the query was actually stored as **`ขอเเบบฟอร์มใช้เเจ้งปลัด...`** with `เเ` (two `เ` characters, U+0E40 ×2).
4. Codepoint inspection: `แ` (U+0E41) count = 0; `เ` (U+0E40) count = 5. Stored text has zero of the character user thought they typed.
5. Likely cause: **Samsung default Thai keyboard** on some Android versions emits `เ` `เ` for the "แ" key instead of one `แ` (U+0E41). Font rendering makes `เเ` and `แ` visually near-identical, so the user can't see the difference.

## The "obvious fix" (Option A)

Replace `เเ → แ` at query entry in `Retriever.retrieve()` so the system sees what the user thought they typed.

```python
def normalize_thai_input(text: str) -> str:
    return text.replace('เเ', 'แ').replace('เ‌เ', 'แ')
```

## Why deploying A alone is wrong

Empirical A/B on prod (2026-05-09), same RAG pipeline, target = ว ๔๙๖ (file_id `1nzNwP7uFYKAM9zbgIEa81RtJ404Oh3Wp`):

| Query (semantically identical to user) | ว ๔๙๖ rank |
|---|---|
| `ขอเเบบฟอร์ม...` (raw, with keyboard typo) | **#4** ✓ |
| `ขอแบบฟอร์ม...` (after normalize, "what user meant") | **NOT in top-30** ❌ |

Stable across 3 reruns — not LLM variance.

The user got a useful answer (LLM cited ว ๔๙๖ in body) **because of** the keyboard typo, not despite it. `เเ` happens to embed close to ว ๔๙๖'s title chunk; `แ` does not. Normalizing destroys that lucky retrieval without giving any compensating gain.

## Real root cause is not the keyboard

The `เเ` vs `แ` ranking gap is downstream of a deeper issue: **`query_expand` (Gemini Flash) produces materially different expansions for inputs that differ by one near-identical character**:

- TYPO version expansions include `แบบฟอร์มแจ้งผู้ทิ้งงาน` + `การขึ้นบัญชีผู้ทิ้งงาน` (specific, pull ว ๔๙๖).
- CORRECT version expansions include the same plus `ปลัดกระทรวงการคลัง`, `กระทรวงการคลัง`, `ระเบียบกระทรวงการคลัง` (broad, pull ministry-related noise that outvotes ว ๔๙๖ at rerank).

Vector pool already has ว ๔๙๖ at #2 (TYPO) vs #9 (CORRECT). After rerank merge across all 8 expanded queries, broad-expansion noise pushes ว ๔๙๖ off-the-list for CORRECT.

So the fix must address query-expansion stability, not just input characters.

## What "deploy A safely" requires

A becomes net-positive when at least ONE of these is in place to compensate:

1. **`ORIGINAL_QUERY_BOOST` raised from 1.3** (currently in `src/config.py`) → original-query results dominate over noisy expansion candidates.
2. **`query_expand` prompt tightened** → forbid extracting standalone broad tokens (`กระทรวงการคลัง` alone is forbidden; expansion must keep paired with action verbs/objects).
3. **Glossary entry** mapping `แบบฟอร์ม`/`แบบแจ้ง` queries → `แบบแจ้งผู้ทิ้งงาน` rescue phrase (with risk noted in `2026-03-10_glossary-expansion-regression.md` — every glossary addition risks regressing other TCs sharing the trigger keyword).

All three would benefit from a 84-TC eval gate before deploy.

## Defer decision (Option F)

Tracked in `ψ/outbox/2026-05-09_pending.md`. Revisit if/when:

- More user complaints arrive showing answer quality degraded for "correctly typed" queries.
- A 84-TC eval baseline pass is scheduled (good time to bundle this fix with the prerequisite tuning).
- Samsung Android user share grows large enough that the silent keyboard bug becomes a measurable retrieval-quality risk.

## Watch-out (general lesson)

When an "obvious correctness fix" exists, A/B test on the empirical case before shipping. Sometimes the broken state has accidentally compensated for an unrelated downstream bug, and fixing the upstream bug exposes the downstream one. Ship the obvious fix only with the downstream fix bundled, or accept that you're trading one regression for another. **Never deploy a "correctness" fix without measuring its retrieval/eval impact first.**

## Related learnings

- `2026-05-09_w496-reocr-pro-v2-pipeline.md` — sibling fix on the same doc (re-OCR worked because that addressed an OCR-side bug, not retrieval-side).
- `2026-03-10_glossary-expansion-regression.md` — earlier example of "obvious fix" backfiring (glossary expansion fixed TC-042 but regressed TC-025).
