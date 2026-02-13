# Thai Legal RAG — Lessons Learned

> จาก `ggnniimm/thai-rag-poc` (ม.ค.–ก.พ. 2569)
> รันกับเอกสารจริง: กรมบัญชีกลาง, ศาลปกครอง, สำนักงานอัยการสูงสุด (700+ ไฟล์)

---

## สิ่งที่พิสูจน์แล้วว่าใช้งานได้

### Stack ที่ดี
- **Gemini embedding-004** (3072 dim) — คุณภาพดี, ฟรี quota พอสำหรับ batch index
- **LightRAG** (graph-based) — ดีสำหรับคำถามที่ต้องเชื่อมหลายเอกสาร เช่น "มาตรการค่าปรับมีขั้นตอนยังไง"
- **FAISS** (vector search) — ดีสำหรับ exact retrieval รวดเร็ว
- **PyThaiNLP `sent_tokenize`** — chunking ถูกต้อง ป้องกันตัดกลางประโยค
- **Gemini 2.0 Flash** — LLM สำหรับ generate answer, ราคาถูก, เร็ว
- **Query Expansion** — สร้าง keyword ภาษาไทยจากคำถาม ช่วย recall มาก

### Domain insights
- เอกสารราชการไทย = สแกน PDF + layer text ปนกัน → ต้องมี OCR fallback
- ศัพท์กฎหมายเฉพาะ (พรบ.จัดซื้อฯ) → Query Expansion ต้องเน้น legal terms
- Persona "นิติกรชำนาญการพิเศษ" ใน system prompt → ตอบสไตล์ถูกต้อง
- PDF scan quality ต่ำ → Tesseract ภาษาไทยไม่ดีพอ → **ควรใช้ Gemini Vision OCR**

---

## สิ่งที่เรียนรู้จากความผิดพลาด

### 1. Flat file structure ฆ่าตัวเอง
```
# สิ่งที่เกิดขึ้น
batch_add_admin_court.py
batch_add_admin_court_md.py
batch_add_ag.py
batch_add_all.py
batch_add_cgd.py
batch_add_lightrag.py
batch_add_lightrag_remaining.py  # <-- เกิดเพราะ retry แล้ว retry
batch_add_missing_cases.py
batch_retry_lightrag.py
...
```
**บทเรียน**: ไม่มี module structure → script สะสมเรื่อยๆ → ไม่รู้ว่าอันไหน canonical

### 2. FAISS + LightRAG ไม่ได้ fuse กัน
- UI ให้ user เลือก "FAISS mode" หรือ "LightRAG mode" เอง
- ควรจะ: query ทั้งสอง → re-rank → merge → ส่งให้ LLM

### 3. No deduplication → index ซ้ำ
- มี `check_faiss_count.py`, `find_missing_*.py`, `recover_*.py` — ล้วนเกิดจากปัญหาเดิม
- ควรมี content hash ก่อน index

### 4. OCR ด้วย Tesseract ภาษาไทยแย่
- เอกสารราชการสแกน → ตัวหนังสือเบี้ยว → Tesseract ล้มเหลว
- **Solution ที่ถูก**: ส่ง PDF pages เป็น image ไปให้ Gemini Vision โดยตรง

### 5. Hardcoded local paths
```python
pdf_dir = "/Users/mingsaksaengwilaipon/.gemini/..."  # โต้งๆ
```
- ทำให้รันบน machine อื่นไม่ได้เลย

### 6. No evaluation
- ไม่รู้ precision/recall จริงๆ
- รู้แค่ "ทดสอบถามแล้วตอบถูก" — ไม่มี systematic eval

---

## Architecture ที่ควรเป็น (Clean)

```
thai-legal-rag/
├── src/
│   ├── ingestion/          # PDF → MD pipeline
│   │   ├── ocr.py          # Gemini Vision OCR
│   │   ├── chunker.py      # Thai-aware chunking
│   │   └── dedup.py        # Content hash deduplication
│   ├── indexing/           # Index management
│   │   ├── faiss_store.py
│   │   ├── lightrag_store.py
│   │   └── manager.py      # Unified interface
│   ├── retrieval/          # Query + fusion
│   │   ├── query_expand.py # Thai legal query expansion
│   │   ├── retriever.py    # Parallel search both stores
│   │   └── reranker.py     # Fuse + re-rank results
│   ├── generation/         # Answer generation
│   │   └── generator.py    # Gemini Flash + legal persona
│   └── config.py           # All config in one place
├── pipeline/               # CLI scripts (thin wrappers only)
│   ├── batch_index.py      # Single canonical batch script
│   └── query.py
├── app/                    # UI
│   └── streamlit_app.py
├── tests/
├── .env.example
└── README.md
```

### Key design decisions
| Decision | Reasoning |
|----------|-----------|
| OCR = Gemini Vision | ดีกว่า Tesseract มาก สำหรับ PDF สแกนภาษาไทย |
| Content hash dedup | ป้องกัน index ซ้ำตั้งแต่แรก |
| Single `IndexManager` | FAISS + LightRAG เป็น implementation detail |
| Fusion retrieval | User ไม่ต้องเลือก mode |
| Config centralized | ไม่มี hardcoded paths |
| Async-first | LightRAG ต้องการ async, FAISS sync wrapper ใส่ thread pool |

---

## Data volumes ที่ผ่านมาแล้ว
- กรมบัญชีกลาง: ~500 ไฟล์ PDF
- ศาลปกครอง: หลายร้อยไฟล์ (มีทั้ง PDF + MD)
- สำนักงานอัยการสูงสุด: indexed แล้ว
- FAISS chunk count: ไม่ทราบชัด (ต้องนับใหม่)

---

*บันทึก: 2026-02-13 | จาก thai-rag-poc review*
