---
title: ## Thai Law Cross-Reference Extraction
tags: [thai-law, regex, cross-reference, metadata]
created: 2026-04-14
source: rrr: gnim-oracle 2026-02-16
---

# ## Thai Law Cross-Reference Extraction

## Thai Law Cross-Reference Extraction

Thai legal sections reference each other with highly consistent patterns:
- `ภายใต้บังคับมาตรา ๕๑` → subordinate_to
- `โดยอนุโลมตามมาตรา ๘` → mutatis_mutandis
- `ตามมาตรา ๕๖` → references (default)

A 30-char lookbehind window captures the keyword reliably — Thai legal phrasing keeps the keyword close to the section reference.

**Key insight**: Regex beats LLMs for structured legal pattern extraction when patterns are consistent. Thai law formatting (ราชกิจจานุเบกษา standard) is remarkably regular — no need for Gemini/GPT for this task.

**Implementation detail**: When adding fields to cached dataclass models, always use `dict.setdefault("new_field", default)` before `ClassName(**dict)` to handle old cache entries gracefully.

**Metric**: 169 out of 365 sections (46%) across 2 Thai procurement laws contained cross-references — showing the dense interconnection typical of regulatory frameworks.

---
*Added via Oracle Learn*
