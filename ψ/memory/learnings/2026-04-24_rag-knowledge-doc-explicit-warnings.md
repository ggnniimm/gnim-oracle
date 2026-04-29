---
title: Knowledge Doc Design for LLM RAG — Explicit Warnings Beyond Formulas
tags: [rag, knowledge-engineering, llm, thai-legal-rag, eval, python]
date: 2026-04-24
source: thai-legal-rag session — fine calculation feature
---

# Knowledge Doc Design for LLM RAG — Explicit Warnings Beyond Formulas

## Core Lesson

When writing knowledge documents for LLM-based RAG, **formulas alone are not enough**. The LLM will read a formula and apply it with assumptions that seem natural but are wrong in the domain. Explicit warning bullets — stating what NOT to do — are required.

## Specific Rules That Had to Be Added (Fine Calculation)

Two TC failures (TC-083, TC-084) revealed that even with correct formulas in the knowledge doc, Gemini made these errors:

1. **TC-083**: Used delivery date (วันส่งมอบ) as Gross endpoint instead of acceptance date (วันผ่านตรวจ) → 41 days instead of 46
   - Fix: Added explicit warning: "Gross endpoint คือวันที่คณะกรรมการตรวจรับผ่าน ไม่ใช่วันที่ผู้รับจ้างส่งมอบ"

2. **TC-084**: Computed deduction2 starting from day after notice of first inspection, not from day after second delivery → 4 days instead of 0
   - Fix: Added explicit rule: "หักตรวจรับแต่ละครั้งนับจากวันถัดจากวันส่งมอบในครั้งนั้น เป็นอิสระจากกัน"
   - Added corollary: "ถ้าส่งมอบและผ่านตรวจในวันเดียวกัน → หักตรวจรับครั้งนั้น = 0 วัน"

## Pattern for Knowledge Doc Structure

For any procedural/calculation domain:

1. **Formula** — necessary but not sufficient
2. **Worked examples** — with complete date-level detail
3. **Explicit warnings** — "X คือ Y ไม่ใช่ Z" format for known confusion points
4. **Edge case annotations** — in the worked examples themselves (e.g., "← ส่งและผ่านวันเดียวกัน → หักได้ 0 วัน")

If a domain expert can get confused on a calculation step, the LLM will too — make the non-obvious explicit.

## Python Unbuffered Output for Long-Running Eval

When running `python3 run_eval.py` with stdout redirected or in a subprocess, output is buffered → user sees nothing during execution.

Fix: always use `python3 -u` to force unbuffered output:
```bash
python3 -u run_eval.py --id TC-081 -v
```

This applies to any long-running script where real-time progress visibility matters.

## Gemini 503 Variance in Full Eval

Full eval with TC-082/083/084 failing is not always a regression. Gemini 2.5 Flash under load falls back to flash-lite (weaker model). Always rerun failing TCs individually with standard model to distinguish variance from regression.

Pattern: run individually → pass = LLM variance; always fail = retrieval or knowledge gap.

## Advisory Opinion as Legal Anchor

กวจ 51349 (กปภ.) confirmed the holiday shifting rule via ป.พ.พ. ม.๑๙๓/๘. Adding `advisory_referenced` frontmatter field to knowledge docs creates a traceable legal basis. Useful for production credibility and future audits.
