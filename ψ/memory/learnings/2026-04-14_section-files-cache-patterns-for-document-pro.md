---
title: ## Section Files + Cache Patterns for Document Processing
tags: [cache, sections, gemini, thai-legal, document-processing, วรรค]
created: 2026-04-14
source: Session — per-section MD files + Gemini วรรค splitting 2026-02-14
---

# ## Section Files + Cache Patterns for Document Processing

## Section Files + Cache Patterns for Document Processing

1. **Belt-and-suspenders for cached processing**: Cache may be generated before processing logic is complete. Apply transformations at both write AND read time for idempotent transforms — safer than trusting cache alone.

2. **Gemini for Thai legal paragraph (วรรค) boundary detection**: PyMuPDF extracts Thai legal text without blank lines between วรรค. Heuristic regex catches some patterns but Gemini Flash is the correct tool. Use fallback: only call Gemini when blank-line split gives 1 วรรค AND content ≥ 300 chars.

3. **Per-section intermediate cache pattern**:
   ```
   full_doc.md (source of truth)
       ↓ auto-generate
   sections/ (intermediate cache, regenerable)
       ├── มาตรา_001.md  ← YAML frontmatter + context header + text
   ```
   Context header helps embedding have law+chapter signal. `regenerate_sections.py` rebuilds from JSON cache without re-OCR.

4. **Thai filenames with diacritics**: Work fine on Linux/macOS filesystems. Be explicit about encoding choice — don't silently simplify.

---
*Added via Oracle Learn*
