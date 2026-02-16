# Lesson: Display changes are cheap when data model is ready

**Date**: 2026-02-16
**Source**: rrr: gnim-oracle
**Tags**: #thai-legal-rag #architecture #incremental-value

## Pattern

When the underlying data model already has the granularity you need (e.g., `LawSection.paragraphs` list populated by Gemini), adding display/rendering features becomes trivial — a few lines of conditional logic. The expensive work is in data extraction; presentation is just formatting.

## Application

The hybrid วรรค display required only 6 lines of Python because:
- Gemini วรรค splitting already populated `sec.paragraphs`
- FAISS chunker already used per-วรรค granularity
- The section MD builder just needed a conditional branch

## Takeaway

Invest in data model completeness early. Once the model captures the right structure, multiple consumers (MD files, FAISS chunks, future APIs) can leverage it independently with minimal code.
