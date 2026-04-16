---
title: ## Docker Compose Deploy and Citation Format Debugging
tags: [docker, streamlit, qdrant, rag, thai-legal-rag, citations, deployment]
created: 2026-04-14
source: Oracle Learn
---

# ## Docker Compose Deploy and Citation Format Debugging

## Docker Compose Deploy and Citation Format Debugging

### Context
Thai Legal RAG — building Streamlit frontend + Docker Compose deployment (2026-03-17).

### Pattern: LLM Citation Format — Check Prompt Before Postprocessing
When LLM doesn't use expected citation format (e.g., uses full document name instead of `[N]`), check the prompt instruction first — not the postprocessing code. LLM was obeying "cite source name" literally. Fix: be explicit: "use [N] format, do NOT write names in body."

### Pattern: Qdrant Local Mode vs Server Mode
- Local mode (`path=`): single-process lock. Only one writer at a time.
- Server mode (`QDRANT_URL`): concurrent access from Streamlit, eval runner, export jobs.
Docker Compose is the clean solution for development — eliminates lock conflicts.

### Pattern: requirements.txt Pinning Causes Docker Build Failures
Local env has compatible packages already installed. Docker starts fresh. Pinned versions can conflict (`google-auth==2.37.0` vs `google-genai>=2.47.0`). Audit: which pins are truly necessary (e.g., numpy for FAISS compat) vs accidental "what was installed that day."

### Pattern: Multi-Source Citation Regex
`_replace_refs` regex must handle comma-separated refs `[1, 14]`, not just single `[N]`. Map each number, dedup source indices.

### Pattern: Shared Logic Duplication Risk
Citation helpers (`_build_source_map`, `_replace_refs`) living in both `streamlit_app.py` and `export_answers_html.py` will diverge. Extract to `src/utils/citations.py` when making any citation change.

---
*Added via Oracle Learn*
