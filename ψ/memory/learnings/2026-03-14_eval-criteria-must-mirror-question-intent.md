---
date: 2026-03-14
source: "rrr: gnim-oracle-embedding-v2"
tags: [eval, must_contain, question-intent, LLM-variance, thai-legal-rag]
---

# Eval criteria must mirror question intent

## Pattern

When writing `must_contain` criteria for RAG evals, each criterion should test what the **question actually asks for** — not what an ideal comprehensive answer would include.

## Observation

TC-011: "ใครเป็นผู้มีอำนาจอนุมัติขยายเวลาทำการ งดหรือลดค่าปรับ" (WHO has authority?)

Had a criterion requiring `[มาตรา 102 | ข้อ 182 | เหตุ 4 ประการ]` — the legal conditions for the approval. This passed when the document containing those conditions (ว52) was retrieved, but failed when it wasn't. The LLM would correctly answer "หัวหน้าหน่วยงานของรัฐ ใช้ดุลพินิจ" (WHO + HOW) without enumerating the conditions (WHY) — a correct answer to a WHO question.

**Fix**: Drop the WHY criterion. Keep only WHO (criterion 1) and HOW/discretion (criterion 3).

## How to apply

When writing or reviewing `must_contain` criteria:

1. Read the question: is it asking WHO, WHAT, HOW, or WHY?
2. For each criterion, ask: "does this test something the question explicitly asks for?"
3. If a criterion tests bonus context not requested by the question → remove it or make it optional
4. Flaky criteria (pass ~80%, fail ~20%) are a signal of intent mismatch, not just LLM variance

## Related

- LLM variance fixes: add alternatives (array-of-arrays) when LLM uses synonyms
- Retrieval-dependent criteria are inherently flaky — if criterion X only passes when doc Y is retrieved, and doc Y is not consistently top-ranked, criterion X will be flaky
