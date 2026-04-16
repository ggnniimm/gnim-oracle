---
date: 2026-03-19
source: "thai-legal-rag eval session: TC-035/045 fix"
concepts: ["generator prompt", "prompt engineering", "rule density", "LLM behavior", "section number citation"]
---

# Generator Prompt Rule Density Has a Practical Ceiling

## Pattern

After ~10-12 rules in a system prompt, additional rules for edge cases require increasingly specific/explicit language to be followed reliably by Gemini Flash.

## Evidence

- Rule 1 said "อ้างอิงข้อกฎหมาย/ระเบียบที่เกี่ยวข้องทุกครั้ง" (cite relevant law/regulation every time)
- TC-035/045 consistently failed: LLM described มาตรา 103 content without citing "มาตรา 103" by number
- Retrieved chunks contained "มาตรา ๑๐๓" multiple times — LLM saw it but didn't include it
- Fix: Added explicit Rule 14: "ให้ระบุหมายเลขมาตราหรือข้อนั้นในคำตอบเสมอ — ห้ามอ้างเฉพาะชื่อ พ.ร.บ. โดยไม่ระบุมาตรา"
- Both TCs immediately PASS after the explicit rule

## Implication

- Abstract rules ("cite relevant law") work for obvious cases but not edge cases
- Specific rules ("cite section numbers, not just law names") are needed when the model consistently misses a pattern
- At 14 rules, we're approaching the practical ceiling — consider consolidating before adding more
- Each new rule competes for the model's attention with existing rules

## When This Matters

- When adding generator prompt rules to fix eval failures
- When the model "should" follow an existing rule but consistently doesn't
- Trade-off: more rules = more edge cases covered, but = less reliable adherence to each individual rule
