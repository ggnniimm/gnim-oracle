---
name: must-contain-answer-direction
description: Eval must_contain must check answer direction (yes/no) — not just keywords — to prevent wrong answers passing
type: feedback
---

# must_contain Must Check Answer Direction

For yes/no questions like "ต้องรอมั้ย" or "เพิ่มค่างานได้มั้ย", must_contain criteria must include the affirmative/negative word that indicates the correct answer direction. Otherwise a factually wrong answer containing the right keywords will still pass.

**Why:** TC-043 asked "ต้องรอผลพิจารณาผู้ทิ้งงานก่อนหรือไม่" — correct answer is "ไม่ต้องรอ". But must_contain only had ["ผู้รับจ้างรายใหม่", "ผู้ทิ้งงาน"], which would pass even if the answer said "ต้องรอ". TC-044 had the same problem — missing the negative "ไม่อาจ/ไม่สามารถ" for a question about whether costs can be increased.

**How to apply:** When writing must_contain for yes/no or can/cannot questions, always include a criterion that captures the answer direction:
- "ไม่ต้องรอ" for "ต้องรอมั้ย → ไม่ต้อง"
- OR["ไม่อาจ", "ไม่สามารถ", "ไม่ได้"] for "ได้มั้ย → ไม่ได้"
- "มีสิทธิ" for "มีสิทธิมั้ย → มี"

Review existing TCs for this pattern when adding new ones.
