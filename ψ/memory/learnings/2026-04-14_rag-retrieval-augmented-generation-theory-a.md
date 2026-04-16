---
title: ## RAG (Retrieval-Augmented Generation) — Theory and Architecture
tags: [rag, retrieval, embedding, chunking, reranking, architecture, theory]
created: 2026-04-14
source: rag.md — deep research 2026-02-12
---

# ## RAG (Retrieval-Augmented Generation) — Theory and Architecture

## RAG (Retrieval-Augmented Generation) — Theory and Architecture

RAG solves 3 main LLM problems: temporal cutoff, private data access, and hallucination. Core idea: separate "knowledge storage" from "linguistic processing" — LLM is a reasoning engine, not an encyclopedia.

**4 Eras of RAG**:
- Naive RAG: proof-of-concept, vector search only; high noise, low precision
- Advanced RAG: pre/post-retrieval refinement; rigid pipeline
- Modular RAG: composable pipeline; complex orchestration
- Agentic RAG: autonomous reasoning, iterative; high latency

**Chunking Strategies**: Fixed-Size (simple prose), Recursive (general docs), Semantic (narrative), Late Chunking (document-aware). Too small = no context, too large = noise.

**High-Performance Retrieval**: Hybrid Search = Dense (vector) + Sparse (BM25). BM25 excels at exact keywords. Reranking = secondary model scores top-K results again (solves "lost in the middle").

**Advanced Techniques**:
- HyDE: LLM generates hypothetical answer → embed that → search from answer space
- Multi-Query RAG: generate alternative phrasings → parallel search → Reciprocal Rank Fusion
- CRAG: if retrieved context is low quality → web search instead
- Self-RAG: model critiques itself with reflection tokens

**RAGAS Evaluation**: Answer Relevance, Faithfulness (hallucination detection), Context Precision, Context Recall.

**Embedding Gap**: Distance between query vector and chunk vector that should be relevant but is far in embedding space. Causes: domain gap, vocabulary dilution (chunk covers multiple topics), perspective gap, corpus imbalance.

**Bi-Encoder vs Cross-Encoder**: Bi-encoder = Stage 1 (fast, retrieve candidates). Cross-encoder = Stage 2 reranker (slower, higher accuracy — reads query+chunk together).

**Cost**: RAG ~$44K/year vs Long Context ~$900K/year for 1M queries. Hybrid (RAG + Fine-tuning) → 88-92% accuracy.

---
*Added via Oracle Learn*
