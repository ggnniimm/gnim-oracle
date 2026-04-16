---
title: ## Eval Tools Must Stay in Sync (run_eval.py ↔ export_answers_csv.py)
tags: [eval, must-contain, tools-parity, thai-legal, or-logic]
created: 2026-04-14
source: Thai Legal RAG session 2026-03-16
---

# ## Eval Tools Must Stay in Sync (run_eval.py ↔ export_answers_csv.py)

## Eval Tools Must Stay in Sync (run_eval.py ↔ export_answers_csv.py)

`run_eval.py` and `export_answers_csv.py` both implement `must_contain` checking separately — must sync features between them.

**Why**: Session 2026-03-16 — export_answers_csv.py supported array-of-arrays (OR logic) already, but run_eval.py didn't. TCs using `["ป.พ.พ.", "ประมวลกฎหมายแพ่ง"]` crashed in run_eval.py only.

**How to apply**: When adding a new feature to must_contain logic in one tool, update the other immediately. Future: extract `_check_case()` as shared utility in `eval/utils.py`.

---
*Added via Oracle Learn*
