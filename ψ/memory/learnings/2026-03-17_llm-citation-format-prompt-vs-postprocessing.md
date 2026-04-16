---
name: LLM citation format — fix the prompt, not the postprocessing
description: When LLM writes full document names instead of [N] references, the bug is in the prompt instruction, not in citation postprocessing code
type: feedback
---

When LLM output doesn't match expected citation format (e.g., writing "(อ้างอิง: ชื่อเอกสาร)" instead of "[N]"), the first thing to check is the system prompt instruction, not the postprocessing code.

**Why:** Rule 5 in generator.py said "อ้างอิงแหล่งที่มา (ชื่อเอกสาร)" — the LLM obeyed literally and wrote the document name. The `_replace_refs` regex was correct but had nothing to replace. Fix was one line in the prompt: explicitly require [N] format and forbid writing names in body.

**How to apply:** When LLM behavior is inconsistent with expected output format, ask "what does the prompt actually say?" before writing postprocessing patches. Prompt engineering bugs look like code bugs but require prompt fixes.
