---
title: ## Data Model Completeness Enables Cheap Display Changes
tags: [architecture, data-model, thai-legal, incremental-value]
created: 2026-04-14
source: rrr: gnim-oracle 2026-02-16
---

# ## Data Model Completeness Enables Cheap Display Changes

## Data Model Completeness Enables Cheap Display Changes

When the underlying data model already has the granularity needed (e.g., `LawSection.paragraphs` list populated by Gemini), adding display/rendering features becomes trivial — a few lines of conditional logic.

The expensive work is in data extraction; presentation is just formatting.

**Applied**: The hybrid วรรค display required only 6 lines of Python because Gemini วรรค splitting already populated `sec.paragraphs`, FAISS chunker already used per-วรรค granularity, and the section MD builder just needed a conditional branch.

**Takeaway**: Invest in data model completeness early. Once the model captures the right structure, multiple consumers (MD files, FAISS chunks, future APIs) can leverage it independently with minimal code.

---
*Added via Oracle Learn*
