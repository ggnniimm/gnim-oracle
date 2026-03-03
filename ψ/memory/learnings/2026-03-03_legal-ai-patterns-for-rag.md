# Legal AI Patterns Applicable to thai-legal-rag

**Date**: 2026-03-03
**Source**: Research on commercial legal AI tools (Spellbook, Harvey, CoCounsel, TrueLaw, Harvard JOLT)
**Tags**: rag, legal-ai, retrieval, chunking, reranking, citation

## Key Patterns from Commercial Legal AI

### 1. Contextual Chunking (Structural, not fixed-size)
- Commercial tools chunk by sections/clauses/logical breaks, not arbitrary char count
- Our system uses CHUNK_SIZE=400 fixed — causes important knowledge to split across chunks (TC-042 bug)
- Improvement: chunk by heading (## ข้อเท็จจริง, ## ข้อวินิจฉัย, ## สรุปข้อวินิจฉัย)

### 2. Prepended Metadata in Chunks (before embedding)
- TrueLaw prepends jurisdiction, court level, date, legal principles into chunk text before embedding
- We already have source_name, category, date in chunk header
- Missing: doc_type, topic, subtopic, laws_referenced
- Adding these to chunk text before embedding improves FAISS semantic matching
- **Highest ROI improvement** — few lines in chunker.py + re-index

### 3. Legal-Aware Reranking
- Commercial tools rerank by: jurisdictional relevance, recency, precedential value
- We can add:
  - **Recency boost** — newer กวจ letters supersede older ones
  - **Doc type weight** — หนังสือเวียน (ว) > ข้อหารือเฉพาะราย (broader policy)
- Currently we only have ORIGINAL_QUERY_BOOST=1.3, no legal-aware factors

### 4. Glossary / Terminology Optimization
- Domain vocabulary alignment between query and documents
- Create glossary of กวจ terms: ผ่อนปรน, ทิ้งงาน, เหมารวม, etc.
- Use in query expansion: "ผ่อนปรน" → "ผ่อนปรนการบอกเลิกสัญญา ข้อ 183"

### 5. Playbook Grounding + Citation Format
- Commercial tools cite by case number/court/date, not filename
- We should cite: "ที่ กค (กวจ) ๐๔๐๕.๔/๑๘๐๗๗ ลว. 24 พ.ค. 2565" instead of filename
- If-Then answer format: "ถ้า...แล้ว...เว้นแต่..." is more actionable for legal advice

## Priority Implementation Order

1. Prepend metadata in chunks (LOW effort, HIGH impact)
2. Auto-anchor generation (MEDIUM effort, HIGH impact) — plan exists
3. Recency boost in reranker (LOW effort, MEDIUM impact)
4. Citation format improvement (LOW effort, MEDIUM impact)
5. Structural chunking by heading (HIGH effort, HIGH impact)
6. Glossary + query expansion (MEDIUM effort, MEDIUM impact)

## Sources

- TrueLaw Contextual Legal RAG: https://www.truelaw.ai/blog/contextual-legal-rag
- Harvard JOLT RAG for Legal: https://jolt.law.harvard.edu/digest/retrieval-augmented-generation-rag-towards-a-promising-llm-architecture-for-legal-work
- Spellbook Legal AI Tools: https://www.spellbook.legal/learn/legal-ai-tools
