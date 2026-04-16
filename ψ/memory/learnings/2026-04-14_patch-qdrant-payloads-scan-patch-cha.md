---
title: เมื่อ patch Qdrant payloads ให้ scan และ patch chat session files ด้วยทันที
tags: [qdrant, session-files, patch, monkey-patch, streamlit-authenticator, thai-legal-rag]
created: 2026-04-14
source: rrr: gnim-oracle-qdrant
---

# เมื่อ patch Qdrant payloads ให้ scan และ patch chat session files ด้วยทันที

เมื่อ patch Qdrant payloads ให้ scan และ patch chat session files ด้วยทันที

Session files (chat_sessions*.json) เก็บ snapshot ของ file_url ตอนที่ query ถูกทำ — ถ้า Qdrant มี old URL session ก็มีด้วย Qdrant patch ไม่ retroactively update sessions

```bash
# หลัง patch Qdrant เสมอ — scan ทุก session file พร้อมกัน
for fname in Path('/app/data').glob('chat_sessions*.json'):
    # replace old urls with mapping[stem]
```

Monkey-patch library: trace full call chain ใน controller ก่อน ไม่ใช่แค่ function ที่เห็นใน error message
- validate_password (gate) ต้อง patch ก่อน
- diagnose_password (message) patch ด้วย

---
*Added via Oracle Learn*
