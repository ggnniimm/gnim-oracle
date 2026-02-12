# RAG (Retrieval-Augmented Generation)

> Source: Gemini Deep Research | 2026-02-12

## What is RAG?

RAG แก้ปัญหาหลักของ LLM 3 อย่าง:
1. **Temporal cutoff** — ข้อมูลเก่า ไม่รู้เรื่องปัจจุบัน
2. **Private data** — เข้าถึง internal/proprietary data ไม่ได้
3. **Hallucination** — สร้างข้อมูลที่ฟังดูสมเหตุสมผลแต่ผิด

แนวคิด: แยก "knowledge storage" ออกจาก "linguistic processing" — LLM เป็น reasoning engine, ไม่ใช่ encyclopedia

---

## 4 ยุคของ RAG

| ยุค | จุดเด่น | ข้อจำกัด |
|-----|---------|----------|
| **Naive RAG** | proof-of-concept, vector search | noise สูง, precision ต่ำ |
| **Advanced RAG** | pre/post-retrieval refinement | pipeline แข็งทื่อ |
| **Modular RAG** | composable pipeline | orchestration ซับซ้อน |
| **Agentic RAG** | autonomous reasoning, iterative | latency สูง, engineering cost |

---

## Chunking Strategies

สำคัญที่สุดใน RAG pipeline — กำหนด granularity ของ retrieval

| Strategy | ความซับซ้อน | ใช้กับ |
|----------|------------|--------|
| Fixed-Size | ต่ำ | prose ทั่วไป |
| Recursive | กลาง | documents ทั่วไป |
| Semantic | สูง | narrative, whitepaper |
| Late Chunking | สูง | ต้องการ document-aware chunks |

- Chunk เล็กเกินไป → ขาด context
- Chunk ใหญ่เกินไป → noise มาก

---

## High-Performance Retrieval

**Hybrid Search** = Dense (vector) + Sparse (BM25)
- BM25 ดีมากสำหรับ exact keyword (product IDs, technical terms)

**Reranking** = secondary model ที่ score top-K results อีกรอบ
- แก้ "lost in the middle" problem

**Vector DB เด่นๆ ปี 2026:**
- **Pinecone** — managed, auto-scale, <100ms latency
- **Milvus** — distributed OSS, trillion-scale
- **Qdrant** — Rust-based, high throughput
- **Weaviate** — multi-modal, built-in vectorization

---

## Advanced Techniques

**HyDE (Hypothetical Document Embeddings)**
- LLM สร้าง "pseudo-document" ที่เป็น ideal answer ก่อน
- ค้นหาจาก embedding ของ answer ไม่ใช่ question

**Multi-Query RAG**
- สร้าง alternative phrasings หลายแบบ
- search parallel + merge ด้วย Reciprocal Rank Fusion (RRF)

**Agentic Patterns:**
- **CRAG** — ถ้า retrieved context คุณภาพต่ำ → web search แทน
- **Self-RAG** — model critique ตัวเองด้วย reflection tokens

---

## Evaluation Metrics (RAGAS)

| Metric | วัดอะไร |
|--------|---------|
| **Answer Relevance** | คำตอบตรง prompt แค่ไหน |
| **Faithfulness** | ทุก claim มีหลักฐานจาก context ไหม (hallucination detection) |
| **Context Precision** | docs ที่ relevant อยู่ top-K ไหม |
| **Context Recall** | retrieved docs ครอบคลุมข้อมูลที่ต้องการไหม |

---

## When to Use RAG?

| สถานการณ์ | วิธีที่ดีที่สุด |
|-----------|--------------|
| Data เปลี่ยนบ่อย (daily/weekly) | **RAG** |
| ต้องการ citations/auditability | **RAG** |
| Offline/edge constraints | Fine-tuning |
| ต้องการ style/behavior เฉพาะ | Fine-tuning |
| Factual accuracy สำคัญ | **RAG** |

**Cost comparison (1M queries/year):**
- RAG: ~$44,400
- Fine-tuning: ~$42,000
- Long Context: ~$900,000 (20-24x แพงกว่า!)

**Hybrid (RAG + Fine-tuning)** → accuracy 88-92% (ดีที่สุด)
