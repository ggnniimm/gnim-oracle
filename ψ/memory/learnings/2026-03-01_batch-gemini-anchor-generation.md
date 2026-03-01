# Batch Gemini Anchor Generation

**Date**: 2026-03-01
**Source**: thai-legal-rag auto-anchor feature
**Tags**: gemini, retrieval, anchors, batch-processing, thai-legal-rag

## Pattern

When you need keyword-dense retrieval summaries for hundreds of documents:
1. Use a simple, constrained prompt: "N keywords + M sentences, plain text only"
2. Truncate input to ~4000 chars (enough context, avoids token waste)
3. Rate limit at 1 req/sec for free-tier Gemini
4. Make idempotent: check if output section already exists before processing
5. Build retry into the workflow (manual `--file` flag or automatic backoff)

## Key Numbers

- 970 files processed in ~52 minutes (3.5 sec/file including 1 sec sleep)
- 99.8% success rate (2 transient 429 failures out of 961)
- 2,163 new chunks from anchors (~2.2 per file)
- Zero eval regressions (8/8 PASS maintained)

## Prompt That Works

```
คำสำคัญ 15-20 คำ + สรุป 2-3 ประโยค
ห้ามใส่หัวข้อ ห้ามใส่ bullet ให้เขียนเป็น plain text เท่านั้น
```

The "plain text only" constraint prevents Gemini from adding markdown formatting that would create noisy chunks.
