# Lesson: Chunk Engineering — Reframing Without Rewriting

**Date**: 2026-02-27
**Source**: thai-legal-rag — กวจ. 20140 positive-duty reframe + ว124 anchor creation

## Pattern

The "บทสรุปสำหรับสืบค้น" section in MD source files serves dual purpose:
1. **Retrieval anchor**: FAISS indexes this as a chunk; keyword density determines sim score
2. **LLM framing**: The text shapes how the LLM interprets and presents the document's content

By engineering this section, you can change LLM output without modifying the legal source text.

## Recipe

```
Line 1: keyword-dense anchor (for retrieval)
Line 2+: framing sentence (for LLM interpretation)
```

Example (กวจ. 20140):
```
อำนาจหน้าที่คณะกรรมการตรวจรับพัสดุ หน้าที่เสนอความเห็นแผน ขอบเขตอำนาจ

คณะกรรมการตรวจรับพัสดุมีหน้าที่เสนอความเห็นเกี่ยวกับแผนการดำเนินงาน...
```

- Line 1 keywords win retrieval (high sim, low dilution)
- Line 2 sentence tells LLM "this is a duty" → LLM frames as "หน้าที่เพิ่มเติม" not "ข้อจำกัด"

## Key Numbers

| Anchor type | Sim score | Retrieval | LLM quality |
|-------------|-----------|-----------|-------------|
| Keywords only | 0.79-0.80 | Excellent | Poor (can't synthesize) |
| Full sentence only | 0.73-0.76 | Often fails | Good when retrieved |
| Keywords + sentence below | 0.79-0.80 | Excellent | Good (reads both) |

The trick: FAISS embeds the whole chunk, but the keyword-dense first line dominates the embedding. The sentence below adds context for LLM without significantly diluting the vector.

## When to Use

- Document has content relevant to a query but LLM frames it wrong
- You want to add a document to an answer without changing the original text
- The desired framing is legitimate (editorial, not fabrication)

## Danger

This is editorial power. You're not changing what the law says — you're changing how the summary presents it. Only use when the framing is defensible and the human understands the distinction.

## Tags

`chunk-engineering`, `anchor-design`, `llm-framing`, `retrieval-vs-generation`, `editorial-not-legal`
