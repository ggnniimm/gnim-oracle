# Always Sample One Qdrant Payload Before Writing Field-Name Queries

**Date**: 2026-04-17
**Context**: Audited production Qdrant for source_name mismatches. First query used field `source` → 0 results. Actual field is `source_name`. Wasted one round-trip.
**Tags**: #qdrant #debugging #field-names #production

## Problem

Qdrant payload field names are set at index time by the pipeline that wrote the chunks. Local code and production may use different field names:
- Local (some code paths): `source`  
- Production: `source_name`

When writing scroll/filter queries, assuming the field name from memory or local code leads to silent 0 results — not an error, just wrong.

## Fix: Sample First

Before any Qdrant query that depends on specific field names:

```python
results, _ = client.scroll(
    collection_name="thai_legal_rag",
    limit=1,
    with_payload=True,
    with_vectors=False,
)
print(results[0].payload.keys())
# → dict_keys(['text', 'file_id', 'source_name', 'file_url', 'category', ...])
```

5 seconds. Saves a failed query round-trip and confusion.

## Production Field Names (verified 2026-04-17)

```
text, file_id, source_name, file_url, category, issued_by, date,
ref_number, topic, subtopic, tags, law_section, section, chunk_index
```

Key: `source_name` (not `source`)

## Related

Same principle applies to any external system with schema ambiguity: always read one record to confirm field names before writing filter queries.
