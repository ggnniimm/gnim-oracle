# Thai Law Cross-Reference Extraction

**Date**: 2026-02-16
**Source**: rrr: gnim-oracle
**Tags**: #thai-law #regex #cross-reference #metadata

## Pattern

Thai legal sections reference each other with highly consistent patterns:
- `ภายใต้บังคับมาตรา ๕๑` → subordinate_to
- `โดยอนุโลมตามมาตรา ๘` → mutatis_mutandis
- `ตามมาตรา ๕๖` → references (default)

A 30-char lookbehind window captures the keyword reliably because Thai legal phrasing keeps the keyword close to the section reference.

## Key Insight

Regex beats LLMs for structured legal pattern extraction when the patterns are consistent. Thai law formatting (ราชกิจจานุเบกษา standard) is remarkably regular — no need for Gemini/GPT for this task.

## Implementation Detail

When adding fields to cached dataclass models, always use `dict.setdefault("new_field", default)` before `ClassName(**dict)` to handle old cache entries gracefully. This was applied in both `extract_law()` and `_load_doc_from_cache()`.

## Metric

169 out of 365 sections (46%) across 2 Thai procurement laws contained cross-references — showing the dense interconnection typical of regulatory frameworks.
