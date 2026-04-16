---
title: ## Post-Processing Beats Prompt Engineering for Deterministic Rules
tags: [nlp, post-processing, prompt-engineering, thai-law, deterministic]
created: 2026-04-14
source: วรรค splitting quality fix 2026-02-17
---

# ## Post-Processing Beats Prompt Engineering for Deterministic Rules

## Post-Processing Beats Prompt Engineering for Deterministic Rules

When you need deterministic behavior (e.g. "always merge list items into parent paragraph"), post-processing is more reliable than trying to get an LLM to follow the rule via prompting. Gemini inconsistently followed "ห้ามแยก sub-items" despite detailed prompts — but a simple regex-based post-processor catches and fixes every case.

**Pattern**:
1. Let AI do what it's good at (semantic paragraph boundary detection)
2. Apply deterministic rules as post-processing (list item merging, orphan fragment detection)
3. Accept AI results even when they seem "too simple" (single-paragraph results are valid)

**Also**: Thai legal structure is hierarchical: ข้อ → วรรค → อนุข้อ (๑)(๒) → sub-items (ก)(ข) → วรรคย่อย. A flat `paragraphs[]` list loses this structure. Future work needs a tree model.

---
*Added via Oracle Learn*
