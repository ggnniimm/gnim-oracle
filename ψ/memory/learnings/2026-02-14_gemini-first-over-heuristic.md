# Gemini-First Over Heuristic for Semantic Tasks

**Date**: 2026-02-14
**Source**: Session — Gemini-first วรรค splitting

---

## Core Lesson

**"Fallback triggered on failure" ≠ "fallback triggered on wrong result"**

Heuristic phase 1 สามารถ "succeed wrongly" ได้ — ให้ผล >1 แต่ semantic ผิด
ทำให้ Gemini fallback ไม่ถูกเรียกเลย แม้ผลจะผิด

→ สำหรับ semantic boundary detection ใดๆ ให้ใช้ LLM ตั้งแต่แรก

---

## Pattern: Two-Phase Trap

```
ถ้าออกแบบ:
  phase 1 (heuristic) → ถ้าผิด → phase 2 (AI)

ต้องถามก่อนว่า:
  "phase 1 สามารถ succeed wrongly ได้ไหม?"
  ถ้าได้ → phase 2 จะไม่ถูกเรียกเมื่อจำเป็น → ใช้ AI ตั้งแต่แรกดีกว่า
```

---

## When Heuristic is OK

- Task ที่ failure ชัดเจน (parse error, empty result)
- Heuristic มี precision สูง แม้ recall ต่ำ
- Cost ของ AI call สูงมากจริงๆ จนต้อง gate

## When Use AI First

- Semantic boundary detection (paragraph, sentence, meaning)
- Thai text ที่ไม่มี lexical markers ชัดเจน
- Cost ของ AI call ต่ำ (Gemini Flash)
