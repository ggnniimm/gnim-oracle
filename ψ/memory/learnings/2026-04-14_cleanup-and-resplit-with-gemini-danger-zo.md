---
title: ## --cleanup and --resplit with Gemini — Danger Zone
tags: [gemini, thai-legal, pipeline, api-key, danger]
created: 2026-04-14
source: Thai Legal RAG pipeline 2026-02-20
---

# ## --cleanup and --resplit with Gemini — Danger Zone

## --cleanup and --resplit with Gemini — Danger Zone

`--cleanup` and `--resplit` in `pipeline/regenerate_sections.py` run Gemini on ALL 355 sections, not just changed ones. If Gemini key is wrong → fallback blank-line split → diffs spike (e.g., 88 → 159).

Env var name is `GEMINI_API_KEY_1_ggnngm` but must be passed as `GEMINI_API_KEY=...` when running.

**Correct run**:
```bash
cd ψ/lab/thai-legal-rag
THAI_RAG_DATA_DIR=$(pwd)/data \
  GEMINI_API_KEY=$(grep "GEMINI_API_KEY_1" /Users/mingsaksaengwilaipon/gnim-oracle/.env | cut -d= -f2) \
  python3 pipeline/regenerate_sections.py --cleanup
```

**Recovery**: If diffs spike after --cleanup, run `--resplit` with correct key to recover.

**Always verify key first**: `python3 -c "import google.generativeai as genai; genai.configure(api_key='KEY'); print('ok')"`

---
*Added via Oracle Learn*
