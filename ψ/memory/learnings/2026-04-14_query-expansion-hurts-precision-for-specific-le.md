---
title: ## Query Expansion Hurts Precision for Specific Legal Queries
tags: [rag, query-expansion, precision, thai-legal, asyncio, api-key-safety]
created: 2026-04-14
source: Thai legal RAG — Option C live test 2026-02-21
---

# ## Query Expansion Hurts Precision for Specific Legal Queries

## Query Expansion Hurts Precision for Specific Legal Queries

Query expansion (expand=True) creates broader queries, causing intro chunks of major laws (พ.ร.บ./ระเบียบ) to score highly and appear in top 5 instead of the specific chunks actually needed.

**Symptom**: Query "ข้อ 11 กฎกระทรวงผู้ประกอบการ" with expand=True → top 5 = พ.ร.บ. มาตรา 1, ระเบียบ ข้อ 1 (wrong). With expand=False → top 5 = กฎกระทรวงฯ ข้อ 11-12 (correct).

**Fix**: Detect "specific" queries and disable expansion:
- Contains section/article number: "ข้อ 11", "มาตรา 60"
- Contains specific law name: "กฎกระทรวง", "ฉบับที่ X"
- Short + specific

**Also**:
- Python 3.10+: `asyncio.get_event_loop()` doesn't create new loop in main thread. Fix: try `get_running_loop()` + `nest_asyncio.apply()`, except `RuntimeError` → `asyncio.run()`.
- Never hardcode API key in bash commands shown in conversation — Google auto-detects and blocks leaked keys. Use `source .env && GEMINI_API_KEY="$GEMINI_API_KEY" python3 ...`

---
*Added via Oracle Learn*
