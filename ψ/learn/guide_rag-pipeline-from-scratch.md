# คู่มือสอน AI สร้าง Document RAG Pipeline จากศูนย์

> เป้าหมาย: ให้ AI อื่นที่เริ่มต้นโปรเจกต์ใหม่แบบไม่มีอะไรเลย สามารถสร้าง pipeline แบบเดียวกับ thai-legal-rag ได้ ครอบคลุมทั้ง coding และ non-coding

---

## ส่วนที่ 1 — Mental Model: เราสร้างอะไร?

### ภาพรวมระบบ

```
PDF ใน Google Drive
   ↓ [download]
   ↓ [OCR: classify + extract → Markdown + YAML]
   ↓ [chunk: section-aware, Thai-aware]
   ↓ [dedup: SQLite hash check]
   ↓ [embed: Gemini 3072-dim vectors]
   ↓ [index: Qdrant (vector) + BM25 (keyword)]
                    ↑ ↓
               [query time]
   ↓ [retrieve: parallel vector + BM25]
   ↓ [rerank: normalize + MMR + source complete]
   ↓ [generate: LLM + citations]
   ↓ คำตอบพร้อม [N] อ้างอิง
```

### ทำไมถึงซับซ้อนแบบนี้?

**ปัญหาที่ต้องแก้**: เอกสารราชการไทยหลายประเภท มีโครงสร้างต่างกัน อ่านยาก OCR ยาก และต้องการคำตอบที่อ้างอิงแหล่งที่มาได้จริง ไม่ใช่แค่สรุป

**ทำไมต้องทำเอง** (ไม่ใช้ off-the-shelf):
- เอกสารภาษาไทย → tokenizer, chunker ต้องใช้ pythainlp
- เอกสารราชการมีโครงสร้างเฉพาะ → OCR prompt ต้องรู้จัก sections
- Hallucination อันตรายในบริบทกฎหมาย → must_contain eval
- ต้องการ link กลับไป source file จริงใน Google Drive

---

## ส่วนที่ 2 — Non-Coding: สิ่งที่ต้องรู้ก่อน code

### 2.1 ทำความเข้าใจ Domain ก่อน

**ถามคำถามเหล่านี้ก่อนเขียน code บรรทัดแรก:**

1. เอกสารของคุณมีกี่ประเภท? แต่ละประเภทมีโครงสร้างต่างกันอย่างไร?
   - ตัวอย่างโปรเจกต์นี้: ข้อหารือ / หนังสือเวียน / คำพิพากษา / ข้อหารืออัยการ
   - แต่ละแบบมี sections ต่างกัน (ข้อเท็จจริง / แนวปฏิบัติ / คำวินิจฉัย)

2. คำถามที่ user ถามคือคำถามประเภทไหน?
   - เฉพาะเจาะจง ("มาตรา 60 บอกว่าอะไร") → ต้องการ keyword precision
   - ทั่วไป ("จัดซื้อจัดจ้างทำอย่างไร") → ต้องการ semantic recall

3. คำตอบที่ผิดมีผลเสียแค่ไหน?
   - กฎหมาย/การเงิน → ผิดพลาดไม่ได้ → ต้องการ citations + eval system เข้มงวด

4. ข้อมูลอยู่ที่ไหน และ access ยังไง?
   - Google Drive, S3, local disk → กระทบ download pipeline
   - PDF, Word, HTML → กระทบ OCR strategy

### 2.2 การตั้งชื่อไฟล์คือ Metadata ชั้นแรก

**Pattern ที่โปรเจกต์นี้ใช้:**
```
001_กวจ_000069_040165_ข้อหารือมาตรการช่วยเหลือ.pdf
     ^^^   ^^^^^^  ^^^^^^
     เลขที่หนังสือ  DDMMYY  (วัน/เดือน/ปี พ.ศ.)
```

**กฎสำคัญ**: ชื่อไฟล์ที่ตั้งโดยผู้ดูแล archive **เชื่อถือได้มากกว่า** OCR
→ ให้ parse ชื่อไฟล์ดึงวันที่, เลขที่หนังสือ แล้ว cross-check กับ OCR output
→ ถ้า OCR ผิด → ใช้ค่าจากชื่อไฟล์แทน (filename is authoritative)

### 2.3 Two-Phase OCR คือการแยก "รู้จักว่าคืออะไร" กับ "อ่านให้ได้"

**Phase 1 (Classification)**: ใช้ model ถูก (Flash) ถามว่า "เอกสารนี้คือประเภทไหน?"
- ข้อมูลน้อย → token น้อย → ถูก + เร็ว
- ผลลัพธ์: กำหนด template ที่จะใช้ใน Phase 2

**Phase 2 (Extraction)**: ใช้ model แรง (Pro) พร้อม template ของ doc type นั้น
- ถ้า document ยาว (>10 หน้า) → แตกเป็น per-page PNG → Pro อ่านทีละหน้า → Pro รวมโครงสร้าง
- ถ้า document สั้น → ส่งทั้งหมดครั้งเดียว

**ทำไมไม่ใช้ Pro ทั้งหมด?** ต้นทุน 50-100x ต่อ call + quota จำกัด

### 2.4 Eval System ต้องสร้างก่อนหรือพร้อมกัน Pipeline

**กฎเหล็ก**: อย่า tune pipeline โดยไม่มี eval
- เพราะ: ทุกการเปลี่ยน configuration อาจ fix TC หนึ่งแต่ break อีก TC
- Eval = "regression test" สำหรับ RAG

**สิ่งที่ต้องมีใน Test Case:**
```json
{
  "id": "TC-001",
  "query": "คำถามภาษาไทย",
  "expected_sources": ["docid1"],
  "must_contain": ["phrase1", ["alt1", "alt2"]],
  "must_not_contain": [],
  "semantic_check": [null, "concept to verify"],
  "notes": "อธิบาย TC นี้"
}
```

**must_contain ต้องรวม answer direction:**
- ผิด: `["ค่าปรับ", "สัญญา"]` (อาจ pass แม้ตอบผิด direction)
- ถูก: `["ไม่ต้องรอ", "ค่าปรับ"]` (รู้ทั้งทิศทางและเนื้อหา)

### 2.5 ระบบ Dedup คือ Safety Net ไม่ใช่ Performance Trick

**ทำไม?** การ index ซ้ำ = ผลลัพธ์ที่ duplicate + เปลืองเงิน embedding
**วิธี**: hash(content) → SQLite → ถ้า hash มีแล้ว → skip

**ข้อควรระวัง**: อย่า run index 2 processes พร้อมกัน (race condition บน SQLite)

---

## ส่วนที่ 3 — Coding: OCR Pipeline

### 3.1 โครงสร้างไฟล์

```
src/ingestion/
├── ocr.py          ← หัวใจหลัก: classify + extract + cache
├── drive.py        ← download PDF จาก Google Drive
├── md_loader.py    ← อ่าน .md ไฟล์ → chunks
├── chunker.py      ← Thai-aware text splitter
├── chunker_law.py  ← Law-specific splitter (ต่อมาตรา)
└── dedup.py        ← SQLite deduplication

pipeline/
├── batch_ocr.py    ← CLI: OCR folder → save .md files
├── batch_index.py  ← CLI: OCR + index ทั้ง pipeline
└── retry_failed_pages.py  ← re-OCR หน้าที่ fail
```

### 3.2 OCR Entry Point Pattern

```python
# ocr.py — ฟังก์ชันหลักที่ pipeline เรียก
def pdf_to_markdown(
    pdf_bytes: bytes,
    file_id: str,
    filename: str,
    force: bool = False,       # force re-OCR แม้มี cache
    per_page: bool = False,    # ใช้ per-page mode สำหรับ long docs
    page_delay: float = 15.0,
) -> dict:
    # 1. Check cache ก่อน
    cached = _load_cache(file_id)
    if cached and not force:
        return cached

    # 2. Phase 1: Classify
    doc_type = classify(pdf_bytes)

    # 3. Phase 2: Extract
    text = extract(pdf_bytes, file_id, filename, doc_type, per_page)

    # 4. Post-process: fix date/docnum from filename
    text = _fix_date_from_filename(text, filename)
    text = _fix_doc_number_from_filename(text, filename)

    # 5. Generate retrieval anchor
    text = text + generate_anchor(text)

    # 6. Save to cache + md_backup
    result = {"text": text, "doc_type": doc_type, ...}
    _save_cache(file_id, result)
    _save_md_backup(filename, text)

    return result
```

### 3.3 Markdown Output Format (Critical)

**ทุก .md file ต้องมี YAML frontmatter ครบ:**

```yaml
---
original_filename: "001_กวจ_000069_040165_...pdf"
doc_type: "ข้อหารือ"          # Ruling_Committee | Circular | Ruling_Court | ...
issued_by: "กวจ."
date: "2022-01-04"            # CE เสมอ (สำหรับ sort + filter)
date_be: "2565-01-04"         # พ.ศ. เสมอ (สำหรับ display)
doc_number: "ที่ กค (กวจ) ๐๔๐๕.๓/๐๐๐๐๖๙"
title: "เรื่อง ..."            # verbatim จากเอกสาร ห้าม paraphrase
topic: "การจัดซื้อจัดจ้าง"
subtopic: "..."
laws_referenced: ["พ.ร.บ.จัดซื้อจัดจ้างฯ มาตรา ๙๗"]
quality: "good"               # good | review-needed | low
quality_note: ""              # เฉพาะ OCR artifact เท่านั้น
page_count: 3
ocr_engine: "gemini-2.5-pro"
ocr_date: "2026-02-22"
status: "active"              # active | inactive
file_id: "1ScQfSkL..."        # Google Drive file ID
file_url: "https://drive.google.com/file/d/.../view"
---
```

**ทำไม date ต้องมีทั้ง CE และ BE?**
- CE → ใช้ sort, filter, recency boost
- BE → เอกสารราชการไทยใช้ พ.ศ. → ต้องแสดงผลถูกต้อง

**Body Structure ตาม doc_type:**
```
## ข้อเท็จจริง          ← verbatim, ห้าม summarize
## ประเด็นข้อหารือ
## ข้อวินิจฉัย          ← สำคัญสุด: ห้ามตัด
## สรุปข้อวินิจฉัย      ← bullet points: ช่วยให้ chunk ถูก retrieve
## บทสรุปสำหรับสืบค้น   ← retrieval anchor: keywords + 2-3 lines summary
```

### 3.4 Retrieval Anchor — สิ่งที่เพิ่ม Recall มากที่สุด

```python
def generate_anchor(text: str) -> str:
    """เพิ่ม section พิเศษท้าย document สำหรับ vector search"""
    # Part 1: Keywords (จาก full text, sample per-chapter สำหรับ long docs)
    keywords = _extract_keywords(text)   # via Gemini Flash
    
    # Part 2: Summary จาก ข้อวินิจฉัย เท่านั้น (ไม่ใช่ทั้งเอกสาร)
    summary = _extract_summary(text)     # via Gemini Flash
    
    return f"\n\n## บทสรุปสำหรับสืบค้น\n{keywords}\n{summary}"
```

**Pattern สำคัญ**: anchor ต้อง keyword-dense บรรทัดแรก → ดี vector score + ดี LLM reading

### 3.5 Long Document Handling

```
ถ้า document > 10 หน้า:
  1. แปลง PDF → PNG ทีละหน้า (300 DPI, PyMuPDF / fitz)
  2. ส่งแต่ละหน้าให้ Pro → ได้ raw text ต่อหน้า
  3. Cache raw text ต่อหน้า (resumable!)
  4. ส่ง raw_pages ทั้งหมดให้ Pro → generate outline (JSON)
  5. Python assembles body จาก outline + raw_pages (deterministic, ไม่ hallucinate)

Fallback chain:
  - 300 DPI timeout → retry 200 DPI
  - API error page X → log to failed_pages.txt → retry later
```

**ทำไม cache raw pages?**
- OCR doc 20 หน้าใช้เวลา ~5 นาที + เงิน
- ถ้า network ตัดตอน page 15 → ไม่ต้องเริ่มใหม่

### 3.6 Caching Strategy

```python
# Cache path: data/ocr_cache/{SHA256(file_id)[:16]}.json
def _cache_path(file_id: str) -> Path:
    return OCR_CACHE_DIR / f"{hashlib.sha256(file_id.encode()).hexdigest()[:16]}.json"

# Raw page cache (per-page OCR mode):
# data/ocr_cache/{hash}_raw.json  ← list of raw page texts
```

**กฎ Cache:**
1. Check cache ก่อนเสมอ
2. Save หลัง postprocess สำเร็จเท่านั้น
3. `force=True` → skip cache (re-OCR)
4. `clear_cache(file_id)` → ลบ cache file นั้น

---

## ส่วนที่ 4 — Coding: Indexing Pipeline

### 4.1 Chunking: Thai-Aware

```python
class ThaiTextSplitter:
    def __init__(self, chunk_size=400, overlap=100):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def split(self, text: str) -> list[str]:
        # ใช้ pythainlp.sent_tokenize(engine="crfcut")
        # สะสม sentences จนถึง chunk_size
        # overlap: เอา sentences สุดท้ายจาก chunk ก่อนมาต่อ
```

**ทำไม chunk_size=400?**
- Gemini embedding context: 2048 tokens
- 400 chars Thai ≈ 200-300 tokens → plenty of room
- น้อยกว่านี้: context ไม่พอ, มากกว่านี้: precision ตก

**Section-Aware Chunking:**
```python
# md_loader.py
def _section_chunks(text: str) -> list[str]:
    # แบ่งตาม ## headers ก่อน
    # แต่ละ section → chunk ตาม size
    # ไม่ข้าม section boundary (ข้อเท็จจริง ไม่ปนกับ ข้อวินิจฉัย)
```

### 4.2 Deduplication System

```python
# dedup.py — SQLite: indexed_chunks table
# CREATE TABLE indexed_chunks (hash TEXT PRIMARY KEY, source_id TEXT, added_at TEXT)

def is_indexed(text: str) -> bool:
    h = hashlib.sha256(text.encode()).hexdigest()
    return db.execute("SELECT 1 FROM indexed_chunks WHERE hash=?", (h,)).fetchone() is not None

def mark_indexed(text: str, source_id: str) -> None:
    h = hashlib.sha256(text.encode()).hexdigest()
    db.execute("INSERT OR IGNORE INTO indexed_chunks VALUES (?,?,datetime('now'))", (h, source_id))

def delete_by_source_id(source_id: str) -> int:
    # ใช้ตอน force-reindex file นั้น
    return db.execute("DELETE FROM indexed_chunks WHERE source_id=?", (source_id,)).rowcount
```

**ข้อผิดพลาดที่พบบ่อย:**
- Force-reindex โดยไม่ delete_by_source_id ก่อน → old chunks ยังอยู่ใน dedup → skip chunks ใหม่
- Run 2 indexer พร้อมกัน → race condition → chunks หาย silently

### 4.3 Embedding + Vector Store

```python
# qdrant_store.py
# Gemini embedding-2 dim=3072, cosine similarity
# Server mode: QDRANT_URL=http://localhost:6333
# Local mode: QDRANT_PATH=data/qdrant_store

def _embed(texts: list[str]) -> np.ndarray:
    # Vertex AI: embed one at a time (API returns 1 embedding regardless of batch size)
    # AI Studio: can batch up to 100
    # Always normalize (L2) before storing
    results = []
    for text in texts:
        r = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
        results.append(r.embeddings[0].values)
    return np.array(results)
```

**Gotcha สำคัญ (Vertex AI):**
- `embed_content(contents=["a","b","c"])` → returns 1 embedding เสมอ (ไม่ใช่ 3)
- ต้อง embed ทีละ text เท่านั้น

### 4.4 BM25 Keyword Store

```python
# bm25_store.py
# rank_bm25.BM25Okapi + pythainlp word tokenizer
# Save/load via pickle: data/bm25_index/bm25.pkl

def add_batch(texts: list[str], metadatas: list[dict]) -> None:
    tokenized = [word_tokenize(t, engine="newmm") for t in texts]
    self.corpus.extend(tokenized)
    self.metadatas.extend(metadatas)
    self.bm25 = BM25Okapi(self.corpus)  # rebuild on every add
```

**ทำไมต้องมี BM25 ด้วย?**
- Vector search: ดี semantic, แย่ exact terms (เลขมาตรา, เลขหนังสือ)
- BM25: ดี exact terms, แย่ paraphrase
- รวมกัน (hybrid): recall สูงสุด

### 4.5 Batch Indexer (Main Pipeline)

```python
# pipeline/batch_index.py
for file in drive.list_pdfs(folder_id):
    pdf_bytes = drive.stream_pdf(file["id"])
    
    # OCR
    result = ocr.pdf_to_markdown(pdf_bytes, file["id"], file["name"])
    
    # Load + chunk
    chunks = md_loader.load_md_file(result["md_path"])
    
    # Dedup check
    new_chunks = [c for c in chunks if not dedup.is_indexed(c.text)]
    if not new_chunks:
        continue  # all chunks already indexed
    
    # Embed + index
    index_manager.add_batch(
        texts=[c.text for c in new_chunks],
        metadatas=[c.metadata for c in new_chunks]
    )
    
    # Mark indexed
    for c in new_chunks:
        dedup.mark_indexed(c.text, file["id"])
```

---

## ส่วนที่ 5 — Coding: Retrieval + Generation

### 5.1 Hybrid Retrieval

```python
# retriever.py
async def retrieve_async(query, expand=True, vector_k=80, history=None):
    # 1. Query expansion (ถ้า query ทั่วไป)
    if expand:
        queries = expand_query(query)   # LLM generates 3-5 variants
    else:
        queries = [query]
    
    # 2. Parallel query ทุก variant พร้อมกัน
    all_results = await asyncio.gather(*[
        index_manager.query_async(q, vector_k, payload_filter) 
        for q in queries
    ])
    
    # 3. Merge + dedup by text content
    # 4. Boost original query results by ORIGINAL_QUERY_BOOST = 1.3
    # 5. Return {"vector": [...], "bm25": [...]}
```

### 5.2 Reranking Pipeline

```python
# reranker.py
def rerank(raw_results, top_k=15, query=""):
    # 1. Normalize scores [0, 1] per source
    # 2. BM25_WEIGHT = 0.9 (near equal to vector)
    # 3. Category boost (ศาลปกครอง → 1.30x)
    # 4. Recency boost (ปีใหม่ → +5%)
    # 5. Dedup by text[:200] (keep best score)
    # 6. MMR (λ=0.7): balance relevance vs diversity
    # 7. Source completion: inject ≤4 chunks from sources already in top-k
    # 8. Return top_k chunks
```

**MMR Formula:**
```
score(chunk) = λ × relevance_score 
             - (1-λ) × max_similarity(chunk, already_selected)

λ=0.7 → 70% relevance, 30% diversity
```

### 5.3 Generator

```python
# generator.py
SYSTEM_PROMPT = """คุณเป็นผู้เชี่ยวชาญด้านกฎหมายจัดซื้อจัดจ้างภาครัฐ
กฎ:
1. อ้างอิงกฎหมาย/ระเบียบทุกข้ออ้างด้วย [N]
2. ห้าม hallucinate — ถ้าไม่มีใน context ให้บอกว่าไม่พบ
3. อนุรักษ์เงื่อนไขและลำดับ (ก่อน/หลัง, ไม่ต้องรอ)
4. แสดงทุกรายการในลิสต์ ห้ามสรุปตัด
5. รักษาตัวเลขและจำนวนเงินตรงตาม context"""

def generate_answer(question, chunks):
    context = build_context(chunks)  # format chunks as [1] ... [2] ...
    # Route: date-calc queries → Pro, others → Flash
    model = _pick_model(question)
    return call_llm(model, SYSTEM_PROMPT, question, context)
```

---

## ส่วนที่ 6 — Coding: Evaluation System

### 6.1 สร้าง Test Cases

```python
# eval/golden_test_cases.json
# เริ่มจาก 10-20 cases, เพิ่มทีละ batch ตาม coverage

# TC format:
{
  "id": "TC-001",
  "query": "คำถาม",
  "expected_sources": ["file_id or doc_number"],
  "must_contain": [
    "phrase_that_must_appear",
    ["alternative1", "alternative2"],  # OR logic
  ],
  "must_not_contain": ["wrong_phrase"],
  "semantic_check": [null, "concept for LLM to verify"],
  "notes": "อธิบาย TC + ทำไมต้องมี"
}
```

### 6.2 Check Logic

```python
# eval/run_eval.py
def check_case(case, answer, sources):
    for phrase in case["must_contain"]:
        if isinstance(phrase, list):
            # OR logic: ผ่านถ้า at least one matches
            passed = any(p in answer_normalized for p in phrase)
        else:
            # AND logic: ต้อง match
            passed = phrase in answer_normalized
        
        if not passed:
            # Semantic fallback: ถาม Gemini Flash ว่า answer cover concept นี้ไหม
            if semantic_concept:
                passed = _semantic_check(answer, semantic_concept)
        
        if not passed:
            return FAIL
    return PASS
```

### 6.3 Run Eval

```bash
# Run ทั้งหมด
THAI_RAG_DATA_DIR=$(pwd)/data python3 eval/run_eval.py

# Run specific TC
THAI_RAG_DATA_DIR=$(pwd)/data python3 eval/run_eval.py --id TC-001 -v

# Retrieval only (no generation, เร็วกว่า)
THAI_RAG_DATA_DIR=$(pwd)/data python3 eval/run_eval.py --no-generate

# Background (สำหรับ full suite ที่ใช้เวลานาน)
THAI_RAG_DATA_DIR=$(pwd)/data python3 eval/run_eval.py > /tmp/eval_out.txt 2>&1 &
# อย่า pipe กับ tail -f → buffer ทำให้ file ว่างจนกว่า process จะจบ
```

---

## ส่วนที่ 7 — Infrastructure

### 7.1 Environment Variables Pattern

```bash
# .env — ทุก config ผ่าน env var เท่านั้น ห้าม hardcode path

# Gemini / Vertex AI
GEMINI_API_KEYS=key1,key2,key3          # rotate เมื่อ quota หมด
GOOGLE_CLOUD_PROJECT=my-gcp-project     # ถ้าตั้ง → ใช้ Vertex AI
GOOGLE_CLOUD_LOCATION=global            # gemini-embedding-2 available on 'global' only
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json  # Service Account for prod

# OCR Model
OCR_EXTRACT_MODEL=gemini-2.5-pro        # ใช้ Pro สำหรับ extraction quality
EMBEDDING_MODEL=gemini-embedding-2      # 3072-dim

# Storage
QDRANT_URL=http://localhost:6333        # ถ้าไม่ตั้ง → local file mode
THAI_RAG_DATA_DIR=/path/to/data         # base directory

# Google Drive
GOOGLE_CREDENTIALS_JSON=credentials.json
DRIVE_FOLDER_CGD=1abc...               # folder IDs ต่อประเภทเอกสาร
```

### 7.2 Docker Setup

```yaml
# docker-compose.yml (dev)
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: [qdrant_data:/qdrant/storage]
  
  app:
    build: .
    environment:
      QDRANT_URL: http://qdrant:6333
    depends_on: [qdrant]
```

**Gotcha สำคัญ:**
- `docker compose restart` ไม่ reload `.env` → ต้องใช้ `docker compose up -d`
- Code change → ต้อง `docker compose build app && docker compose up -d app`
- อย่าใช้ embedded Qdrant กับ >10K chunks ใน Docker → RAM เต็ม

### 7.3 Google Drive OAuth Flow

```python
# drive.py
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def _get_credentials():
    token_path = Path(GOOGLE_TOKEN_JSON)
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if creds.expired:
            creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_JSON, SCOPES)
        creds = flow.run_local_server(port=0)  # opens browser
    
    token_path.write_text(creds.to_json())
    return creds
```

### 7.4 Vertex AI vs AI Studio

```
AI Studio (GEMINI_API_KEYS):
  + ง่าย: แค่ API key
  - Quota น้อย
  - เหมาะ: dev, prototype

Vertex AI (GOOGLE_CLOUD_PROJECT + ADC/SA):
  + Quota สูงกว่ามาก (embedding: ~435 calls/min vs ~7-10/min)
  + Billing control ชัดเจน
  - ต้อง setup GCP project + SA
  - เหมาะ: production

Toggle ใน code:
  if os.getenv("GOOGLE_CLOUD_PROJECT"):
      # Vertex AI path
  else:
      # AI Studio path
```

---

## ส่วนที่ 8 — Pitfalls และ Lessons Learned

### 8.1 OCR Pitfalls

| ปัญหา | สาเหตุ | แก้ไข |
|-------|--------|-------|
| OCR date ผิด | Pro อ่าน เลขไทย ผิด | Parse จากชื่อไฟล์แทน |
| Long doc timeout | >10 หน้า ส่ง single call | Switch เป็น per-page mode |
| Truncated output | Streaming timeout page กลาง | Cache raw pages, resume |
| Template ผิด | Classify ผิด doc_type | Filename override (ว ใน filename → Circular) |

### 8.2 Indexing Pitfalls

| ปัญหา | สาเหตุ | แก้ไข |
|-------|--------|-------|
| Chunks หาย | 2 indexer parallel (race condition) | ห้าม run parallel |
| Force-reindex ไม่ work | ลืม delete_by_source_id ก่อน | ลบ dedup records ก่อน force reindex |
| Local eval pass แต่ prod fail | Local กับ prod มี corpus ต่างกัน | Run eval บน prod เสมอ |
| Docker ไม่ pick env | docker compose restart แทน up | ใช้ `up -d` เสมอ |

### 8.3 Retrieval Pitfalls

| ปัญหา | สาเหตุ | แก้ไข |
|-------|--------|-------|
| TC fail intermittently | LLM variance (ไม่ใช่ retrieval) | เพิ่ม must_contain alternatives |
| TC consistent fail | Corpus ไม่มี doc นั้น | ตรวจว่า file indexed ไหม |
| Glossary expansion regression | เพิ่ม term → รบกวน TC อื่น | Test ก่อน-หลัง ทุกครั้ง |
| Cross-ref injection ไม่ work | ใส่ใน anchor แต่ anchor ไม่ถูก retrieve | ใส่ใน CONTENT sections |

### 8.4 Eval Pitfalls

| ปัญหา | สาเหตุ | แก้ไข |
|-------|--------|-------|
| must_contain pass แต่ตอบผิด | ไม่รวม answer direction | เพิ่ม "ไม่ต้องรอ", "ไม่อาจ" |
| Flaky TC → "intermittent" | จริงๆ fail consistent ใน prod | Run 3 ครั้งบน prod ก่อนสรุป |
| Semantic_check pass แต่ wrong | LLM too lenient | ใช้ must_contain เป็น primary |

---

## ส่วนที่ 9 — Step-by-Step สำหรับ AI ที่เริ่มใหม่

### ขั้นตอนแนะนำ (ทำตามลำดับ)

```
Week 1: Foundation
  ☐ สร้าง src/config.py — env vars ทั้งหมด
  ☐ สร้าง src/ingestion/drive.py — download PDF จาก Google Drive
  ☐ สร้าง src/ingestion/ocr.py — classify + extract (short docs only)
  ☐ ทดสอบ OCR บน 5 เอกสาร, verify frontmatter ถูกต้อง

Week 2: Indexing
  ☐ สร้าง src/ingestion/chunker.py — Thai text splitter
  ☐ สร้าง src/ingestion/md_loader.py — parse frontmatter + chunk
  ☐ สร้าง src/ingestion/dedup.py — SQLite dedup
  ☐ สร้าง src/indexing/qdrant_store.py — Gemini embedding + Qdrant
  ☐ สร้าง src/indexing/bm25_store.py — BM25 + pythainlp
  ☐ สร้าง pipeline/batch_index.py — tie everything together
  ☐ Index เอกสาร 50 ไฟล์แรก

Week 3: Retrieval + Eval
  ☐ สร้าง src/retrieval/retriever.py — hybrid retrieve
  ☐ สร้าง src/retrieval/reranker.py — MMR
  ☐ สร้าง src/generation/generator.py — answer with citations
  ☐ สร้าง eval/golden_test_cases.json — 10 TCs แรก
  ☐ สร้าง eval/run_eval.py — eval runner
  ☐ Run eval, tune จนได้ baseline

Week 4: Long Docs + Production
  ☐ เพิ่ม per-page OCR mode (PyMuPDF + page cache)
  ☐ เพิ่ม retrieval anchor generation
  ☐ Docker setup (Qdrant server + app)
  ☐ Deploy + run full eval บน prod
```

### สิ่งที่ควรมีในทุก script

```python
#!/usr/bin/env python3
"""
batch_ocr.py — OCR PDFs from Google Drive folder → .md files

Usage:
    THAI_RAG_DATA_DIR=$(pwd)/data python3 pipeline/batch_ocr.py \
        --folder-id DRIVE_FOLDER_ID \
        --output-dir data/md_backup \
        --limit 100
"""
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # ก่อน import src modules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder-id", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    
    # ... logic here
    
    # Always print summary at end
    logger.info(f"Done: {processed} processed, {skipped} skipped, {failed} failed")

if __name__ == "__main__":
    main()
```

---

## Summary

| หัวข้อ | Key Insight |
|--------|-------------|
| **OCR** | 2-phase (Flash classify → Pro extract), filename authoritative, cache aggressively |
| **Markdown** | YAML frontmatter + verbatim sections + retrieval anchor |
| **Chunking** | 400 chars, section-aware, pythainlp sentence tokenizer |
| **Dedup** | SHA256 hash → SQLite, delete before force-reindex |
| **Embedding** | gemini-embedding-2, dim=3072, global endpoint, one text at a time (Vertex) |
| **Retrieval** | BM25 + vector parallel, merge by text content, ORIGINAL_QUERY_BOOST=1.3 |
| **Reranking** | MMR λ=0.7, source completion, category boost |
| **Eval** | must_contain + answer direction, run on prod not local, 3 runs to confirm flaky |
| **Infrastructure** | All config via env vars, docker compose up (not restart), no parallel index |
