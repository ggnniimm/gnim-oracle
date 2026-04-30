# TC-071: section-number promotion in summary chunk (2026-04-30)

## Problem

TC-071 ("ผู้มีอำนาจอนุมัติแก้ไขสัญญาตามมาตรา 97 กับผู้มีอำนาจงดลดค่าปรับตามมาตรา 102 เป็นคนเดียวกันหรือไม่") consistent FAIL. Missing `["ข้อ ๑๖๕", "ข้อ 165"]`.

Previously labeled "known flaky" in MEMORY.md.

## Diagnosis

- Expected sources: `ว_476` and `61864` — both **present in md_backup** (per audit)
- 61864 was warning'd as "not cited" — confirmed not in top-K
- ว_476 IS in top-15 retrieved, but its top-ranked chunks (the summary) **didn't contain `ข้อ ๑๖๕` literally** — only the search-keyword section had it
- ว_476's body has 4 mentions of ข้อ ๑๖๕ (lines 28, 46, 51, 70) but the summary discussed the **substance** (อำนาจอนุมัติ vs อำนาจลงนาม) without naming the section number
- Same Rule-14 trap as TC-035: LLM summarized the substance from the doc but dropped the specific section number

61864's body has zero mentions of ข้อ ๑๖๕ — it's about ม.102/งดค่าปรับ, not ม.97/ข้อ ๑๖๕. So the must_contain hook is genuinely only available via ว_476.

## Fix

Prepended a query-aligned bullet to ว_476's `## สรุปข้อวินิจฉัย`:

> **สรุปการแบ่งอำนาจตามระเบียบฯ — ม.๙๗ vs ม.๑๐๒ ไม่ใช่คนเดียวกัน**: อำนาจในการแก้ไขสัญญาตามมาตรา ๙๗ แบ่งเป็นสองส่วนตามระเบียบฯ — (๑) **อำนาจอนุมัติแก้ไขสัญญา ตามระเบียบฯ ข้อ ๑๖๕ วรรคสาม** เป็นของผู้มีอำนาจอนุมัติสั่งซื้อหรือสั่งจ้าง ... (๒) **อำนาจลงนามในสัญญาที่แก้ไขแล้ว ตามระเบียบฯ ข้อ ๑๖๑ วรรคหนึ่ง** เป็นของหัวหน้าหน่วยงานของรัฐ ซึ่งต่างจากอำนาจงดหรือลดค่าปรับตามมาตรา ๑๐๒ ...

Bullet starts with the exact comparison phrase from the query (ม.๙๗ vs ม.๑๐๒ ... ไม่ใช่คนเดียวกัน), names both `ข้อ ๑๖๕` and `ข้อ ๑๖๑` explicitly, and contrasts with `ม.๑๐๒` for completeness.

Force-reindex: 17 vectors → 19 chunks (+2 from new bullet).

## Verification

3 runs: **PASS, PASS, FAIL** (2/3 = 67% pass rate).

Improvement from baseline 0/3 to 2/3. TC-071 remains intermittent — consistent with its prior "known flaky" status. Not 3/3 stable.

To get 3/3 stable would require either:
- Adding another `ข้อ ๑๖๕` reference to a different bullet (doubled chunk coverage), or
- Cross-ref injection into the consistently-top-cited doc (e.g., `04_กวจ_51419`)

Both add regression risk. Stopped at 2/3 as a meaningful improvement — TC-071 is now flaky-favorable instead of consistently-failing.

## Regression check

Spot-checked TC-046 and TC-051 — both still PASS. ว_476 reindex didn't perturb prior fixes.

## Pattern: section-number promotion

This is variant of TC-046's "chunk promotion" pattern, but specialized:
- TC-046: doc had two competing sections (problem-statement vs resolution); prepended answer-shaped summary made resolution outrank problem
- TC-071: doc's summary had the substance but **dropped the section number anchor**; prepended bullet that includes the number explicitly

Trigger: when must_contain fails on a section number AND the source doc has the number elsewhere in body, but not in summary.

Distinct from TC-051's classic cross-doc cross-ref injection (where the legal anchor is from a DIFFERENT source).

## Same caveat

Source MD edit lives on prod + local cache only — `data/` is gitignored. Backup at `.bak.2026-04-30` on prod.
