---
title: ## Thai Legal RAG Design Lessons
tags: [thai-legal, rag, pdf-parsing, metadata, embedding]
created: 2026-04-14
source: Session retrospective 2026-02-14
---

# ## Thai Legal RAG Design Lessons

## Thai Legal RAG Design Lessons

1. **PDF format determines parser**: ราชกิจจานุเบกษา formats เลข มาตรา 1-9 on separate line from "มาตรา" (`มาตรา\n๑`) but มาตรา 10+ on same line. Regex that doesn't know this silently misses sections. Fix: `_normalize_section_headers()` handles both forms.

2. **Vision AI vs Text Parser for Thai law**: PyMuPDF + Gemini fallback beats LandingAI for structured Thai law (132 vs 115 section coverage). LandingAI only valuable for bounding boxes or scan-only PDFs.

3. **Metadata schema for multi-type RAG**: Core fields for all doc types: `doc_type`, `date`, `date_be`, `topic`, `laws_referenced`, `status`. Bridge field `laws_referenced` enables "มาตรา 56 มีหนังสือหารืออะไรบ้าง" queries. Type-specific: พ.ร.บ. → `law_name`, `law_year_be`; หนังสือหารือ → `issued_by`, `doc_number`, `quality`.

4. **Context header in chunk helps embedding**: Instead of embedding "มาตรา ๕๖ ..." alone, prepend `[พ.ร.บ.จัดซื้อจัดจ้างฯ 2560 | หมวด ๕]` — gives law + chapter signal for better retrieval.

5. **Schema origins may be in conversation, not commits**: When tracing design decisions, the schema may originate from conversation before the commit — don't under-claim contribution.

---
*Added via Oracle Learn*
