---
title: ## Amendment-Aware RAG via Prompt Engineering (Option C)
tags: [rag, amendments, thai-law, prompt-engineering, versioning]
created: 2026-04-14
source: Thai legal RAG — กฎกระทรวง batch OCR session 2026-02-21
---

# ## Amendment-Aware RAG via Prompt Engineering (Option C)

## Amendment-Aware RAG via Prompt Engineering (Option C)

When FAISS index contains multiple versions of the same law (BASE + amendments), LLM needs to know which version is latest.

**Option C — Prompt Engineering** (MVP, no re-indexing required):
1. Ensure `law_year_be` is in FAISS metadata for every chunk
2. Surface `law_year_be` in context string sent to LLM: `f"[{i}] **{source}** [พ.ศ. {law_year_be}] ({category})\n{text}"`
3. Add rule to system prompt: "หากมีหลายฉบับในปี พ.ศ. ต่างกัน ให้ยึดฉบับ พ.ศ. สูงสุด (ล่าสุด) เป็นหลัก"

**Trade-offs** (A: consolidation, B: status metadata+filter, C: prompt engineering):
- Option A: slow, best quality, requires re-index
- Option B: medium speed, good quality, requires re-index
- Option C: fast MVP, acceptable quality, no re-index needed

Ceiling: FAISS still retrieves old-version chunks, consuming context window.

**Related**: กฎกระทรวง signature is `ให้ไว้ ณ วันที่` (vs พ.ร.บ.'s `ประกาศ ณ วัน`). `_SIGNATURE_BLOCK_RE` must handle both.

---
*Added via Oracle Learn*
