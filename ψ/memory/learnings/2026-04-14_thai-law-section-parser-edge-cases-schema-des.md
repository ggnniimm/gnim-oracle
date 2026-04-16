---
title: ## Thai Law Section Parser Edge Cases + Schema Design (2026-02-14)
tags: [thai-law, pdf-parsing, section-parser, schema-design, vision-ai, caching, rag]
created: 2026-04-14
source: retro: 2026-02-14 law-extractor-metadata-design
---

# ## Thai Law Section Parser Edge Cases + Schema Design (2026-02-14)

## Thai Law Section Parser Edge Cases + Schema Design (2026-02-14)

**PyMuPDF ครบ แต่ layout กำหนด parser**: Text extraction may be complete but PDF page layout directly affects section parsing. มาตรา 1-9 had "มาตรา" and "๑" on separate lines, while มาตรา 10+ were on same line. Single-digit section numbers are a common edge case in Thai law PDFs.

**Vision AI vs Text Parser tradeoff for Thai law**: LandingAI (vision AI) sees images and layout but captures fewer sections (115 vs 132 มาตรา) for structured Thai law. Text parser + smart regex wins for Thai legal documents with clear section hierarchy.

**Schema design for cross-document RAG**: `topic` and `laws_referenced` are bridge fields that enable cross-document queries. Context header prepended to each chunk gives embedding better signal. Core fields should be consistent across all document types (ข้อหารือ, พ.ร.บ., ระเบียบ).

**Experiment results need caching**: Running LandingAI 4-5 times on 42 pages (2 min each) because first result wasn't cached. Always save JSON result after first successful run — same principle as OCR cache.

**Don't under-claim AI contribution**: When tracing git history to determine who designed something, a Ming commit may be the result of a prior conversation with the Oracle. The schema came from Gnim's research, Ming refined it — both contributed.

---
*Added via Oracle Learn*
