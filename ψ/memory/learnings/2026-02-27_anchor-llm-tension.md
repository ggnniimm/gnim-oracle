# Lesson: Anchor-LLM Tension — Retrieval Win ≠ Generation Win

**Date**: 2026-02-27
**Source**: thai-legal-rag TC-003 × กวจ. 20140 — anchor engineering session

## Pattern

There is a fundamental tension between anchor text optimized for **retrieval** vs text optimized for **LLM generation**:

| Goal | Optimal text | Result |
|------|-------------|--------|
| Beat title in retrieval | Short, dense keywords matching query | High sim score, anchor retrieved |
| LLM generates phrase | Complete sentence with context | LLM can paraphrase/quote |

These two goals pull in opposite directions because:
- Embedding models reward **keyword density** — fewer words = less dilution = higher cosine similarity
- LLMs need **complete sentences** to synthesize meaningful content — keyword lists get ignored

## Evidence

Tested 15+ anchor candidates for กวจ. 20140 "แผน" case:

| Anchor | Retrieval | LLM says แผน |
|--------|-----------|-------------|
| cx5 (keywords: "เสนอความเห็น แผน หน้าที่ ขอบเขต") | 5/5 ✓ | 0/10 ✗ |
| cx9 (phrase: "หน้าที่เสนอความเห็นแผน ขอบเขตอำนาจ") | 5/5 ✓ | 1/10 ✗ |
| cs1 (sentence: "กรณีสัญญากำหนดแผนการดำเนินงาน มีหน้าที่เสนอความเห็น") | 1/5 ✗ | untested |
| v2 (full sentence from document) | 0/5 ✗ | works when retrieved |

Adding just "การดำเนินงาน" (2 words) to cx5 dropped retrieval from 5/5 → 2/5.

## When This Applies

- Document has a **strong title chunk** (sim > 0.82) that any anchor must beat
- The desired phrase is **semantically distant** from the query keywords
- Query is **broad** ("หน้าที่อะไรบ้าง") while the target phrase is **specific** ("แผนการดำเนินงาน")

## Right Approach

When anchor-LLM tension exists:
1. **Don't force the phrase into the broad TC** — it will never be stable
2. **Create a specific TC** with a query that directly targets the document/phrase
3. **Accept the trade-off**: broad TC gets the document as source; specific TC validates the phrase content

Example:
- TC-003 (broad): "หน้าที่และขอบเขตอำนาจ" → expected_sources includes 20140 ✓
- TC-004 (specific): "กรณีสัญญากำหนดแผนการดำเนินงาน" → must_contain "แผนการดำเนินงาน" ✓ (3/3 stable)

## Additional Finding: Isolation Test ≠ Actual FAISS

Always test anchor sim with the **full stored chunk format** (metadata header + content), not just the content text. Metadata header "[ที่ กค (กวจ) 0405.3/20140 | 20140 | 2023-06-13 | ข้อหารือ]\n\n" dilutes both title and anchor equally but changes absolute margins.

Isolation test gave 6/6 wins; actual FAISS stored vectors gave 5/5 (different margins).

## Tags

`anchor-llm-tension`, `retrieval-vs-generation`, `embedding-dilution`, `eval-design`, `must_contain`, `tc-design`
