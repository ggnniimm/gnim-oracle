# LightRAG — Quick Reference

> Explored: 2026-02-12 09:01

## What is LightRAG?

LightRAG คือ RAG framework ที่ผสม **knowledge graph** กับ **vector search** ต่างจาก standard RAG ตรงที่ extract entity-relationship ระหว่าง index document เพื่อสร้าง knowledge graph ทำให้ retrieval เข้าใจทั้ง local context และ global knowledge ได้ดีกว่า

## Installation

```bash
pip install lightrag-hku
# หรือ
uv pip install lightrag-hku

# Server mode
pip install "lightrag-hku[api]"

# Docker
docker compose up  # ต้องมี .env
```

## Query Modes

| Mode | การทำงาน |
|------|---------|
| `local` | Context-dependent — ค้นจาก entity neighbors |
| `global` | Global knowledge — ค้นจาก graph summaries |
| `hybrid` | Local + Global รวมกัน |
| `mix` | Knowledge graph + vector retrieval |
| `naive` | Vector search ธรรมดา (ไม่ใช้ graph) |
| `bypass` | ข้าม retrieval — LLM โดยตรง |

## Key Features

- Dual-level retrieval (KG + vector)
- Entity-relationship extraction ตอน index
- Reranker support
- Multimodal document processing (RAG-Anything)
- Citation & traceability
- Web UI สำหรับ explore graph
- Ollama-compatible API
- RAGAS evaluation + Langfuse tracing

## Storage Backends

| ประเภท | ตัวเลือก |
|--------|---------|
| KV | JsonKV (default), PostgreSQL, Redis, MongoDB |
| Vector | NanoVectorDB (default), PGVector, Milvus, Faiss, Qdrant, Chroma |
| Graph | NetworkX (default), Neo4j, PostgreSQL+AGE |

## Configuration

```python
rag = LightRAG(
    working_dir="./cache",
    llm_model_func=gpt_4o_mini_complete,
    embedding_func=openai_embedding,
    kv_storage="JsonKVStorage",       # หรือ PGKVStorage, RedisKVStorage
    vector_storage="NanoVectorDBStorage",  # หรือ MilvusVectorDBStorage
    graph_storage="NetworkXStorage",  # หรือ Neo4JStorage
    chunk_token_size=1200,
    enable_llm_cache=True,
)
```

## When to Use LightRAG vs Standard RAG

**ใช้ LightRAG เมื่อ:**
- ต้องการ multi-hop reasoning ข้ามหลาย entities
- ต้องการเข้าใจ relationships ระหว่าง entities
- ต้องการทั้ง factual retrieval และ conceptual understanding
- ต้องการ structured knowledge representation

**ใช้ Standard RAG เมื่อ:**
- Simple keyword/semantic lookup
- resource จำกัด
- ไม่ต้องการ graph complexity

## Performance Notes

- **Production**: Neo4j ให้ผลดีกว่า PostgreSQL+AGE
- **LLM แนะนำ**: 32B+ parameters, 32KB+ context (64KB ดีสุด)
- **Embedding แนะนำ**: BAAI/bge-m3 หรือ text-embedding-3-large
- **Reranker แนะนำ**: BAAI/bge-reranker-v2-m3
- Python 3.10+ required
