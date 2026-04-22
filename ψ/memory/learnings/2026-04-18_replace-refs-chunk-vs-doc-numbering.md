---
name: _replace_refs must match build_context numbering scheme
description: When build_context() uses per-doc numbering, _replace_refs must not remap via chunk indices
type: feedback
date: 2026-04-18
---

`_replace_refs` in streamlit_app.py was remapping `[N]` citation numbers using a `chunk_to_src` dict (chunk index → source number). This was correct when the generator used per-chunk numbering.

After `build_context()` switched to per-document numbering (`[N]` = Nth unique source), `_replace_refs` became wrong: with 22315 having 13 chunks in the context, citations [2]–[13] all remapped to source 1 (22315), making the LLM's `[1], [4]` appear as `[1], [1]` in the rendered output.

**Fix**: `_replace_refs` should only deduplicate citation numbers, never remap them.

```python
def _replace_refs(answer: str) -> str:
    def replace(m):
        nums = list(dict.fromkeys(int(x.strip()) for x in m.group(1).split(",")))
        return "[" + ", ".join(str(i) for i in nums) + "]"
    return re.sub(r"\[([\d ,]+)\]", replace, answer)
```

**Why:** The generator and app both group chunks by source_name in the same order — their numbering is already consistent. No remapping needed.

**How to apply:** Whenever `build_context()` numbering scheme changes (per-chunk ↔ per-doc), audit `_replace_refs` immediately.
