---
title: ## OCR Pipeline + Gemini SDK Migration Lessons (2026-02-13)
tags: [gemini, sdk, ocr, prompt-engineering, codespace, oauth, api-migration]
created: 2026-04-14
source: retro: 2026-02-13 thai-legal-rag-ocr-pipeline
---

# ## OCR Pipeline + Gemini SDK Migration Lessons (2026-02-13)

## OCR Pipeline + Gemini SDK Migration Lessons (2026-02-13)

**Gemini LLM instruction specificity**: Vague instructions = LLM takes shortcuts. "ห้ามสรุป" is not enough — must say "ห้ามอ้างอิงกลับ" (no back-references like "as described above"). The more explicit the constraint, the less creative the LLM gets.

**Defensive post-processing for Gemini output**: Gemini sometimes outputs invalid YAML (`  - key: value` instead of `key: value`). Always add `_fix_frontmatter()` regex post-processing — don't trust structured output to be valid.

**google.genai SDK migration**: API pattern changed subtly from `google.generativeai`:
- Old: `genai.configure(api_key=key)` → function-level calls
- New: `client = genai.Client(api_key=key)` → `client.models.*`
- Embeddings: `result["embedding"]` → `result.embeddings[0].values`

**Gemini File API >> page-by-page image rendering**: For Thai legal PDFs, sending whole PDF via File API gives significantly better OCR quality than per-page image rendering.

**Codespace = headless**: Any feature requiring browser auth (OAuth2, Google login) will fail in Codespace. Always design auth flow assuming headless first. Google OAuth2 OOB flow was deprecated since 2022 — use service account + JSON key for server-side pipelines.

**Test before migrating SDK**: Write a short test that exercises the key API calls (embeddings format, model calls) BEFORE migrating all 5+ files. Saves multiple failed attempts.

---
*Added via Oracle Learn*
