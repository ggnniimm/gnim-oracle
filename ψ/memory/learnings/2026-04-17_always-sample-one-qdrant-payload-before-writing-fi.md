---
title: Always sample one Qdrant payload before writing field-name queries.
tags: [qdrant, payload, field-names, debugging, production, schema, deprecated-flags]
created: 2026-04-17
source: rrr: gnim-oracle
---

# Always sample one Qdrant payload before writing field-name queries.

Always sample one Qdrant payload before writing field-name queries.

Qdrant payload field names are set at index time — local code and production may differ:
- Some local code uses: `source`
- Production uses: `source_name`

Wrong field → silent 0 results (not an error). Easy to waste a round-trip debugging.

Fix: before any scroll/filter query, run:
```python
results, _ = client.scroll(collection_name="thai_legal_rag", limit=1, with_payload=True, with_vectors=False)
print(results[0].payload.keys())
```

Production field names (verified 2026-04-17):
text, file_id, source_name, file_url, category, issued_by, date, ref_number, topic, subtopic, tags, law_section, section, chunk_index

Also: when a CLI flag/feature is marked deprecated/removed from code, update mental model immediately — stop suggesting it in commands. "Deprecated, ignored" in code ≠ OK to keep typing. (Caught by Ming: --no-lightrag still in suggested commands after b85a3f9 cleaned it up.)

---
*Added via Oracle Learn*
