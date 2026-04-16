---
title: ## Amendment-Aware RAG + API Key Safety (2026-02-21)
tags: [rag, amendment, api-key, prompt-engineering, query-expansion, audit, reference-data, thai-legal]
created: 2026-04-14
source: retro: 2026-02-21 to 2026-02-22 amendment + audit sessions
---

# ## Amendment-Aware RAG + API Key Safety (2026-02-21)

## Amendment-Aware RAG + API Key Safety (2026-02-21)

**Amendment-aware RAG via prompt engineering (Option C)**: Simplest solution — add `[พ.ศ. XXXX]` tag to each chunk's context in `build_context()` and add system prompt rule: "if multiple versions retrieved, cite the latest year." No re-indexing needed — just surfaces `law_year_be` metadata already in FAISS.

**Three amendment handling options**: A (consolidation — merge to single file), B (status metadata — filter superseded at retrieval), C (prompt engineering — LLM picks latest year). Option C is fastest MVP but has a ceiling: if retrieval layer drops amendment chunks before LLM sees them, Option C can't help.

**Query expansion hurts precision for specific legal queries**: expand=True creates broader queries that boost intro chunks (high keyword density) over specific กฎกระทรวง chunks. For queries with specific section numbers, disable expansion.

**Never hardcode API keys in bash commands**: API key typed as plaintext in bash command in conversation → Google detects and blocks immediately. Always pass via `source .env` or `$ENV_VAR`. Never hardcode, never paste into conversation.

**Reference data can be wrong**: "3 diffs remaining as OCR ceiling" → turned out Excel reference was wrong (มาตรา 66, 68, 69). Always cross-check reference against official law text before labeling as "unfixable OCR gap."

**Signature block regex must handle multiple keywords**: กฎกระทรวง uses `ให้ไว้ ณ วันที่`, พ.ร.บ. uses `ประกาศ ณ วัน`. Both must be in `_SIGNATURE_BLOCK_RE`. Different document types have different footer formats.

**Audit heuristics need ground-truth validation before scaling**: Always spot-check 3-5 flagged items manually BEFORE running automated fixes on 30+ files. Running fix_truncated_ocr.py on 26 files took 55 minutes for files that turned out to be fine.

---
*Added via Oracle Learn*
