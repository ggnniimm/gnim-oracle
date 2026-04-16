---
title: ## RAG for Thai Legal Documents — Research and Stack Recommendations
tags: [rag, thai-legal, architecture, embedding, knowledge-graph, chunking, temporal-rag, benchmarks]
created: 2026-04-14
source: rag-thai-legal.md — deep research 2026-02-12
---

# ## RAG for Thai Legal Documents — Research and Stack Recommendations

## RAG for Thai Legal Documents — Research and Stack Recommendations

Thai Legal RAG is hard because: Thai has no word spaces (chunking cuts mid-word), heavy cross-references (section → section → regulation), laws change frequently, specialized legal vocabulary with precise definitions, LCLMs (long context) still lose to RAG on NitiBench.

**Recommended Stack**:
- Embedding: BGE-M3 (human-finetuned) — Recall@1 = 73.3% on Thai legal
- Retrieval: BM25 (exact keywords like มาตรา ๕๖) + Dense (BGE-M3) + Cross-Encoder reranker
- Chunking: Hierarchy-aware — PyThaiNLP tokenize → parse structure (ภาค → หมวด → มาตรา → วรรค) → 300-600 tokens per chunk. Prepend lineage metadata in each chunk.

**Knowledge Graph (NitiLink Pattern)**:
- Lexical Graph: document hierarchy
- Relational Graph: cross-references bidirectional ("อ้างถึงใคร" AND "ใครอ้างถึงเรา")
- Multi-agent: Router → Recursive Retrieval → Definition → Answering Agent

**Temporal RAG**: Use CTV (Conceptual Temporal Version) + CLV (Conceptual Language Version) nodes. Filter active CTV for current queries, reconstruct past state for historical queries.

**LLM Recommendations**: Claude 3.5 Sonnet (accuracy), Typhoon 2 70B (Thai-centric), Chinda Thai LLM 4B (on-premise, data sovereignty).

**GRPO Alignment** (fixes citation hallucination): Format Reward + Grounded Citation + Semantic Similarity rewards → Citation-F1 +90%, joint quality +31%. Best output structure: Reasoning → Answer → Citation.

**Cost estimate (Thai government scale)**: Setup ~350K THB, 89% accuracy, 3.2s response, +45% productivity.

---
*Added via Oracle Learn*
