# LightRAG — Architecture

> Explored: 2026-02-12 09:01

## What is LightRAG?

LightRAG เป็น lightweight, production-ready RAG framework ที่ใช้ **graph-based knowledge representation** สำหรับ retrieval ที่ดีกว่า standard RAG โดยการ extract entities และ relationships จาก documents เพื่อสร้าง knowledge graph แล้วทำ multi-modal retrieval (local, global, hybrid, naive, mix) เพื่อ ground LLM responses ในบริบทที่มีโครงสร้าง

## Directory Structure

```
LightRAG/
├── lightrag/                    # Core package
│   ├── lightrag.py              # Main LightRAG orchestrator class
│   ├── base.py                  # Abstract storage base classes
│   ├── operate.py               # Core extraction, merging, query logic
│   ├── types.py                 # Data types (KnowledgeGraphNode, Edge)
│   ├── prompt.py                # LLM prompt templates
│   ├── utils.py                 # Utilities (tokenization, embeddings, caching)
│   ├── rerank.py                # Reranking logic
│   │
│   ├── api/                     # FastAPI server & REST API
│   │   ├── lightrag_server.py
│   │   └── routers/
│   │
│   ├── kg/                      # Storage implementations (pluggable)
│   │   ├── networkx_impl.py     # In-memory graph (default)
│   │   ├── neo4j_impl.py
│   │   ├── postgres_impl.py
│   │   ├── mongo_impl.py
│   │   ├── redis_impl.py
│   │   ├── qdrant_impl.py
│   │   ├── milvus_impl.py
│   │   └── faiss_impl.py
│   │
│   └── llm/                     # LLM provider integrations (13 providers)
│       ├── openai.py, anthropic.py, ollama.py, gemini.py, bedrock.py ...
│
├── lightrag_webui/              # React 19 + TypeScript frontend
└── examples/                   # 15+ usage examples
```

## Core Abstractions

**Storage Layer** — 4 pluggable backend types:
- `BaseKVStorage` — LLM cache, text chunks, entity/relation metadata
- `BaseVectorStorage` — Entity, relationship, chunk embeddings
- `BaseGraphStorage` — Entity-relationship graph structure
- `BaseDocStatusStorage` — Document processing state

**Query Modes:**
```
LOCAL   → Community detection on entity neighbors
GLOBAL  → High-level entity summaries + community abstracts
HYBRID  → Combines local + global
MIX     → Full KG path + chunked docs + reranking
NAIVE   → Fallback vector-only search
```

## Architectural Innovation

### สิ่งที่ LightRAG ทำต่างจาก Standard RAG

1. **Dual-Level Knowledge Graph**
   - Extract entities AND relationships (ไม่ใช่แค่ chunks)
   - Store เป็น graph structure → traversal relationships ได้
   - Entity-centric + relationship-centric retrieval

2. **Incremental Merging**
   - Entities/relations จาก chunks ต่างๆ ถูก deduplicate และ merge
   - Descriptions accumulate ข้าม documents หลายชิ้น
   - LLM-guided merging ลด hallucination

3. **Query Flow**
   ```
   User Query
     ↓ Extract Keywords (High-level + Low-level)
     ↓
   [LOCAL]  → Vector search entities → Expand to neighbors
   [GLOBAL] → Vector search summaries → Aggregate communities
     ↓ Combine contexts → [Optional Reranker] → LLM generation
   ```

4. **Pluggable Storage** — Development ใช้ JSON, Production ใช้ Neo4j/PostgreSQL/MongoDB
5. **Async throughout** — ไม่มี blocking I/O
6. **LLM Response Caching** — MDHash-based

## Key Dependencies

- `networkx` — in-memory graph (default)
- `nano-vectordb` — lightweight vector DB (default)
- `tiktoken` — token counting
- `fastapi` — REST API
- Optional: neo4j, pymongo, asyncpg, pymilvus, qdrant-client, faiss
