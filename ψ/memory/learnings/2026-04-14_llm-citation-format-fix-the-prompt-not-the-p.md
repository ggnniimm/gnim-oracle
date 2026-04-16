---
title: ## LLM Citation Format — Fix the Prompt, Not the Postprocessing
tags: [prompt-engineering, citation, llm, generator, postprocessing]
created: 2026-04-14
source: Thai Legal RAG citation format fix 2026-03-17
---

# ## LLM Citation Format — Fix the Prompt, Not the Postprocessing

## LLM Citation Format — Fix the Prompt, Not the Postprocessing

When LLM output doesn't match expected citation format (e.g., writing "(อ้างอิง: ชื่อเอกสาร)" instead of "[N]"), first check the system prompt instruction, not the postprocessing code.

**Why**: Rule 5 in generator.py said "อ้างอิงแหล่งที่มา (ชื่อเอกสาร)" — LLM obeyed literally and wrote the document name. The `_replace_refs` regex was correct but had nothing to replace.

**Fix**: One line in prompt — explicitly require [N] format and forbid writing names in body.

**How to apply**: When LLM behavior is inconsistent with expected output format, ask "What does the prompt actually say?" before writing postprocessing patches. Prompt engineering bugs look like code bugs but require prompt fixes.

---
*Added via Oracle Learn*
