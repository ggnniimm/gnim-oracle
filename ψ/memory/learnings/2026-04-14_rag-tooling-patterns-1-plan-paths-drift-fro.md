---
title: ## RAG Tooling Patterns
tags: [rag, tooling, streamlit, git, ocr-cache]
created: 2026-04-14
source: Thai Legal RAG tooling layer session 2026-02-13
---

# ## RAG Tooling Patterns

## RAG Tooling Patterns

1. **Plan paths drift from reality**: Always verify paths against the filesystem before implementing. When mismatch found, create a bridge (wrapper/redirect) — moving files breaks other things.

2. **exec() redirect for Streamlit**: When Streamlit needs to run file at path A but canonical app is at path B, use `exec(app_path.read_text(), {"__file__": str(app_path)})` in the `else` branch. The `__file__` override is critical for relative path resolution.

3. **Query CLI for RAG testing**: Before UI is ready, a CLI query tool is more useful than full Streamlit. Key flags: `--no-generate` (pure retrieval, no LLM cost), `--no-expand`, show scores/sources/Drive links.

4. **Never `git add .` in lab directories**: Lab dirs mix code + data + credentials. Always explicit `git add <file>` and scan `git status` first.

5. **OCR cache keyed by SHA256(file_id)**: When file re-uploaded to Drive, file_id changes — old cache remains for old ID. `clear_cache(file_id)` removes permanently; `--force` flag bypasses at extraction time.

---
*Added via Oracle Learn*
