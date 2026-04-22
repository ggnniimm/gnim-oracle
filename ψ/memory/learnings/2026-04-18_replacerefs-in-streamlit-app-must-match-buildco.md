---
title: _replace_refs in Streamlit app must match build_context() numbering scheme. When
tags: [rag, citation, streamlit, bug, numbering]
created: 2026-04-18
source: rrr: thai-legal-rag
---

# _replace_refs in Streamlit app must match build_context() numbering scheme. When

_replace_refs in Streamlit app must match build_context() numbering scheme. When build_context() uses per-document numbering ([N] = Nth unique source), _replace_refs must NOT remap via chunk_to_src dict. With many chunks per source, citations [2]–[13] all remap to source 1, making [1],[4] appear as [1],[1]. Fix: deduplicate only, no remapping.

---
*Added via Oracle Learn*
