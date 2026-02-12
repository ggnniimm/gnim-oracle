# RAG สำหรับเอกสารกฎหมายไทย

> Source: Gemini Deep Research | 2026-02-12
> Use case: หนังสือราชการ, คำพิพากษา, คำวินิจฉัยอัยการสูงสุด, พ.ร.บ.จัดซื้อจัดจ้าง, ระเบียบ, กฎกระทรวง

---

## ทำไม Thai Legal RAG ถึงยาก

1. **ภาษาไทยไม่มีช่องว่างระหว่างคำ** — chunking ธรรมดาจะตัดกลางคำ
2. **Cross-references หนาแน่น** — มาตราอ้างมาตรา, กฎอ้างกฎ, คำวินิจฉัยอ้างมาตรา
3. **กฎหมายเปลี่ยนบ่อย** — แก้ไขเพิ่มเติม, ยกเลิก, ฉบับใหม่ทับฉบับเก่า
4. **ศัพท์เฉพาะทาง** — "ราคากลาง", "วิธีเฉพาะเจาะจง" มีนิยามตามกฎหมาย ≠ ความหมายทั่วไป
5. **LCLMs ยังสู้ RAG ไม่ได้** — แม้ Gemini 1.5 Pro จะรับ 2M tokens ได้ แต่ NitiBench แสดงว่า RAG แม่นกว่า

---

## Stack ที่แนะนำ

### 1. Embedding Model

**BGE-M3 (human-finetuned)** — ดีที่สุดสำหรับ Thai legal text
- รองรับ Thai-English code-switching
- Benchmark: Recall@1 = 73.3% บน Thai legal datasets
- ทางเลือก: Cohere embed-multilingual-v3.0, E5

### 2. Retrieval: Hybrid Search

```
Sparse (BM25)   → ค้น exact keywords: "มาตรา ๕๖", เลขหนังสือ
Dense (BGE-M3)  → ค้น semantic: query ภาษาพูด → ข้อความกฎหมาย
Cross-Encoder   → Rerank top-K จาก BM25+BGE-M3 รวมกัน
```

Cross-encoder reranker: `BGE-based Cross-Encoder`

### 3. Chunking: Hierarchy-Aware

**ห้ามใช้ fixed-size chunking กับภาษาไทย**

ขั้นตอน:
1. **PyThaiNLP** tokenize ก่อน (newmm engine หรือ deepcut)
2. Parse โครงสร้างด้วย regex: ภาค → หมวด → มาตรา → วรรค → อนุมาตรา
3. Chunk = 1 มาตรา/วรรค (ไม่ตัดกลาง)
4. Chunk size: **300-600 tokens** (ไทยหนาแน่นกว่าอังกฤษ)
5. Prepend lineage metadata ใน chunk: `"พ.ร.บ. จัดซื้อฯ หมวด ๖ มาตรา ๕๖ วรรค ๒:"`

Metadata ที่ inject ทุก chunk:
```json
{
  "act": "Procurement Act B.E. 2560",
  "chapter": "6",
  "section": "56",
  "paragraph": "2",
  "effective_date": "2560-08-24",
  "status": "active"
}
```

---

## Knowledge Graph: NitiLink Pattern

### ทำไมต้องใช้ Graph

มาตรา A อ้างมาตรา B → vector search หาแค่ A ไม่พอ ต้องดึง B มาด้วย

### 2 Graph ที่ต้องมี

**1. Lexical Graph** (Document Hierarchy)
```
พ.ร.บ. จัดซื้อฯ → หมวด 6 → มาตรา 56 → วรรค 2
```

**2. Relational Graph** (Cross-References)
```
มาตรา 56 ──อ้างถึง──→ มาตรา 67
มาตรา 67 ──อ้างถึง──→ ระเบียบกระทรวงการคลัง ข้อ 15
```

ต้องทำ **bidirectional** — รู้ทั้ง "อ้างถึงใคร" และ "ใครอ้างถึงเรา"

### Multi-Agent Retrieval

```
Query → Router Agent
         ↓ (ตรวจ cross-reference)
    Recursive Retrieval Agent → traverse graph
         ↓
    Definition Agent → ดึง นิยาม จากหมวด 1
         ↓
    Answering Agent → generate with full context
```

Framework: LangGraph / LlamaIndex + Neo4j

---

## Temporal RAG: จัดการฉบับแก้ไข

### ปัญหา

Vector search ไม่รู้ว่า "มาตรา 5 (2560)" ถูกแทนที่โดย "มาตรา 5 (2566)" แล้ว

### Solution: CTV + CLV Nodes

| Node | ความหมาย |
|------|---------|
| **Component Node** | แนวคิดกฎหมายนามธรรม (ไม่มีฉบับ) |
| **CTV** (Conceptual Temporal Version) | เนื้อหาช่วงเวลาหนึ่ง (มีวันที่เริ่ม-สิ้นสุด) |
| **CLV** (Conceptual Language Version) | ข้อความจริงที่ link กับ CTV |

**Query ปัจจุบัน** → filter เฉพาะ CTV ที่ active
**Query อดีต** → reconstruct ข้อความตามวันที่

ตัวอย่างการตรวจจับการแก้ไข:
- `"ให้ยกเลิกความในมาตรา..."` → สร้าง CTV ใหม่, mark CTV เก่าว่าสิ้นสุด
- `"ให้เพิ่มความต่อไปนี้..."` → append CLV ใหม่

---

## Legal NER: Entity ที่ต้อง Extract

| Entity | ตัวอย่าง | ประโยชน์ |
|--------|---------|---------|
| **Statutory Reference** | "ตามมาตรา ๒๑ วรรคสอง" | สร้าง cross-reference graph |
| **Temporal (พ.ศ.)** | "พ.ร.บ. ๒๕๖๐", "มีผลบังคับ ๑ ม.ค. ๒๕๖๑" | Temporal filtering |
| **หน่วยงาน** | "กรมบัญชีกลาง", "นายกรัฐมนตรี" | Jurisdictional filtering |
| **นิยามศัพท์** | "ราคากลาง", "วิธีเฉพาะเจาะจง" | Definition graph |

---

## LLM สำหรับ Production

| Model | จุดเด่น | ใช้เมื่อ |
|-------|---------|---------|
| **Claude 3.5 Sonnet** | accuracy สูงสุด | zero-shot, ไม่มี data sovereignty issue |
| **Typhoon 2 70B** | Thai-centric, NitiBench-Tax ดี | cloud deployment |
| **Chinda Thai LLM 4B** | on-premise, 98.4% Thai output | รัฐบาลที่ต้อง data sovereignty |
| **OpenThaiGPT 1.5** | Qwen2.5 base, 2M Thai instructions | on-premise |

**Chinda LLM** แนะนำสำหรับ government:
- 4B params, BF16
- Context 32K (ขยายถึง 131K ด้วย YaRN)
- Deploy ด้วย Ollama/vLLM/SGLang
- มี Thinking Mode `<think>...</think>`

---

## GRPO Alignment: แก้ Citation Hallucination

ปัญหา: LLM อ้าง มาตรา ที่ไม่มีใน context → ผิดกฎหมาย

Solution: **Group-Relative Policy Optimization (GRPO)**

| Reward | กลไก |
|--------|------|
| **Format Reward** | ถ้า format ถูก = 1, ผิด = 0 |
| **Grounded Citation** | อ้างจาก context จริง = 0.5, hallucinate = 0 |
| **Semantic Similarity** | BGE-M3 เปรียบกับ ground truth |

ผล: Citation-F1 เพิ่ม **90%**, joint quality เพิ่ม **31%**

Output structure ที่ดีที่สุด: **Reasoning → Answer → Citation** (ไม่ใช่ Citation ก่อน)

---

## Benchmark

**NitiBench** — มาตรฐานวัด Thai Legal RAG

| Dataset | เนื้อหา | ความยาก |
|---------|---------|---------|
| NitiBench-CCL | กฎหมายการเงิน/บริษัท 35 ฉบับ | ปานกลาง |
| NitiBench-Tax | คดีภาษี 50 คดี, เฉลี่ย 3 มาตราต่อคดี | สูงมาก |

---

## Cost ประมาณการ (Thai Government Scale)

- Setup: ~350,000 บาท
- Accuracy: 89% (well-tuned system)
- Response time: 3.2 วินาที
- Productivity: +45%
- vs Long Context (Gemini 1.5 Pro): RAG ถูกกว่า 20-24x

---

## สรุป Architecture สำหรับ พ.ร.บ.จัดซื้อฯ

```
Documents (PDF/Word)
  ↓ PyThaiNLP tokenize
  ↓ Hierarchy-aware chunking (มาตรา-level)
  ↓ Legal NER (section refs, dates, agencies, definitions)
  ↓
[KV Store]     [Vector DB]      [Knowledge Graph]
chunks+meta    BGE-M3 embeddings  Neo4j (Lexical + Relational)
                                  + Temporal CTV/CLV nodes
  ↓
Query Pipeline:
  User query → NER → metadata filter → Hybrid Search (BM25+Dense)
  → Rerank → Graph Traversal → Definition Agent
  → LLM (Chinda/Typhoon2) with GRPO alignment
  → Response: Reasoning → Answer → Citation
```
