---
title: ## Legal AI Patterns for RAG (from Commercial Tools)
tags: [legal-ai, rag, retrieval, chunking, citation, reranking]
created: 2026-04-14
source: Research on commercial legal AI tools 2026-03-03
---

# ## Legal AI Patterns for RAG (from Commercial Tools)

## Legal AI Patterns for RAG (from Commercial Tools)

Key patterns from Spellbook, Harvey, CoCounsel, TrueLaw:

1. **Contextual chunking** (structural, not fixed-size): chunk by sections/clauses/logical breaks (## ข้อเท็จจริง, ## ข้อวินิจฉัย, ## สรุปข้อวินิจฉัย) not arbitrary char count.

2. **Legal-aware reranking**: recency boost (newer letters supersede older), doc type weight (หนังสือเวียน > ข้อหารือเฉพาะราย).

3. **Glossary / terminology optimization**: align domain vocabulary between query and documents. Use query expansion with legal synonyms.

4. **Citation format**: cite by case number/court/date ("ที่ กค (กวจ) ๐๔๐๕.๔/๑๘๐๗๗ ลว. 24 พ.ค. 2565") not filename.

5. **If-Then answer format**: "ถ้า...แล้ว...เว้นแต่..." is more actionable for legal advice.

**Priority**: Prepend metadata in chunks (LOW effort, HIGH impact) → Auto-anchor generation → Recency boost → Citation format → Structural chunking.

---
*Added via Oracle Learn*
