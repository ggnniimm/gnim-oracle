---
title: ## Section-Restricted Anchor Generation + Source Expansion Failure
tags: [rag, anchors, hallucination, retrieval, source-expansion, thai-legal-rag, debugging]
created: 2026-04-14
source: Oracle Learn
---

# ## Section-Restricted Anchor Generation + Source Expansion Failure

## Section-Restricted Anchor Generation + Source Expansion Failure

### Context
Thai Legal RAG — anchor hallucination fix (2026-03-08). Gemini OCR was conflating ข้อเท็จจริง with ข้อวินิจฉัย in generated summaries.

### Pattern: Section-Restricted Anchor Generation
Split anchor generation into two prompts:
1. Keywords: feed full document text (8K window), extract 25-30 keywords
2. Summary: feed ONLY ข้อวินิจฉัย section, write 2-3 sentences

This prevents conflating background facts with the actual ruling.

### Pattern: Correct Anchors ≠ Good Retrieval Anchors
Factually correct summaries may lack keyword density needed for FAISS retrieval. Old hallucinated summaries were accidentally keyword-rich. Solution: semantic bridge sentences (natural language connecting query concepts to document concepts) work better than keyword packing.

### Pattern: Source Expansion is Net-Negative
Pulling extra chunks from documents already in top-K floods LLM context with noise. 15 MMR-selected chunks + source completion is sufficient. Source expansion caused 44→31/48 regression when combined with other injection mechanisms.

### Pattern: Test Features in Isolation Before Combining
Three injection mechanisms (source completion + glossary injection + source expansion) each seemed helpful alone but were catastrophic together. Test each in isolation, measure, then decide whether to combine.

### Pattern: Distinguish Retrieval Failures from Generation Failures
If right chunks are in LLM context but expected phrase is missing from answer, it's a generation problem — no retrieval engineering will fix it.
**Signal**: rebuild shows right doc retrieved → TC still fails → STOP retrieval engineering.
Cross-reference injection works for retrieval gaps only, not for LLM summarization choices.

---
*Added via Oracle Learn*
